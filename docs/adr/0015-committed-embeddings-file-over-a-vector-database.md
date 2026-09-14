# ADR-0015: A committed embeddings file, not a vector database, for assistant retrieval

## Status

Proposed

## Context

The read-only chat assistant (`backend/app/services/assistant_llm.py`, PR #45)
answers questions about AAGP. Ungrounded, it answers them from whatever the base
model already believes about "AI governance platforms" — fluent, plausible, and
not about this system. It needs the repository's own paragraphs to quote, with a
citation a reader can check.

That is a retrieval problem, and the reflex answer to a retrieval problem is a
vector database. The forces here point elsewhere:

- The corpus is small and fixed. `docs/SYSTEM-EXPLAINED.md`, `docs/CONTEXT.md`,
  fifteen ADRs and `shared/reason_codes.py` come to roughly 131,000 characters —
  about **135 chunks**. A brute-force scan over 135 vectors is 135 dot products,
  which is microseconds of arithmetic, not a workload.
- The corpus changes when somebody edits a document, which is a handful of times
  a week and never during a request.
- This project has already ruled on exactly this shape of question. ADR-0008
  chose in-process library calls over four deployed services for prototype
  scope, and `docker-compose.yml` carries a comment saying Redis, Celery and the
  observability stack were cut and need an ADR to come back. Adding pgvector or
  Chroma to search 135 chunks would be the same decision reversed without the
  circumstances changing.
- Deadline: 15 September 2026. A new service is a new thing to stand up in the
  demo environment, and a new way for the demo to fail in front of a panel.

## Decision

**Retrieval is a committed `assistant/index.json` plus cosine similarity in pure
Python. No vector database, no new service, no numeric stack.**

The index is built by a deliberate CLI (`python -m assistant build`), reviewed as
a diff, and committed — the same shape as `python -m governance.record` and the
recordings under `governance/recordings/`. Searching it is one embedding call for
the query and a dot product against each stored vector.

Detail that matters:

- **Chunks split on markdown headings** — and, inside a glossary, on each
  `**Term** —` definition — not on fixed character windows. An ADR's
  `Context`, `Decision` and `Consequences` are each a complete argument; a
  500-character window cuts one in half and hands the assistant a reason with its
  conclusion missing. Each chunk carries its heading path, so a citation reads
  "ADR-0006 > Decision", or "System Explained > 3. Glossary > Cooldown", rather
  than "chunk 47".
- **Embeddings go through the existing provider layer.** `GeminiEmbeddingClient`
  lives in `governance/llm/gemini.py` beside the chat client it shares its key
  handling, `x-goog-api-key` header rule, `Pacer` and error hierarchy with. There
  is one LLM integration in this repository and this does not add a second.
- **Gemini only.** Anthropic publishes no embedding model; OpenAI's is paid, and
  `docs/lanes/vc.md` forbids introducing a paid service while ADR-0012's ruling
  on the optional paid *chat* providers is still Proposed. Selecting another
  provider raises rather than falling back.
- **A staleness guard.** Every source's SHA-256 is stored with its chunks and the
  loader warns loudly — `python -m assistant check` exits non-zero, and CI runs
  it — when a document has changed, been added, or been removed since the build.
  This lane has had this bug once already: a prompt edited in place without a
  version bump replayed the old wording and looked perfectly healthy, which is
  why `RecordingStaleError` exists.
- **A relevance threshold, measured.** `RELEVANCE_THRESHOLD = 0.62`
  (`assistant/index.py`). Five questions the docs answer scored 0.702–0.761 on
  their best chunk; four they do not ("how do I bake sourdough bread", "what is
  our Kubernetes ingress configuration", …) scored 0.510–0.575. Nothing landed
  between. A caller getting nothing above it should say it has nothing on the
  subject rather than serving the best of a bad set as though it were an answer.

## Consequences

- **Nothing new to deploy, and the demo cannot lose its retrieval to a container
  that did not come up.** The index is a file in the repository; loading it is
  reading JSON.
- **Search is offline except for the query embedding.** One network call per
  question, none per chunk. `search_vector()` is pure.
- **The index must be rebuilt when the docs change, and forgetting is now a CI
  failure** rather than a silent wrong answer (`.github/workflows/ci.yml`,
  "assistant index is current with the docs").
- **Cost: `assistant/index.json` is 1.2 MB of committed artifact**, and it churns
  wholesale whenever a document is edited. Mitigated, not eliminated: vectors are
  written one per line rather than one float per line, which is a third off the
  size a plain `json.dumps(..., indent=1)` produces, and the
  chunk text above each vector diffs a line at a time so a reviewer can still see
  what changed. A repository that already commits LLM recordings can carry this;
  a corpus ten times the size could not, and that is the point at which this
  decision needs revisiting rather than stretching.
- **Cost: 768 dimensions, not 256.** Truncating the same vectors to 256
  dimensions would quarter the file, and it narrows the gap the threshold lives
  in from 0.127 to 0.065 — at 128 dimensions the off-topic questions score
  0.75–0.78 and the threshold stops separating anything. The file size is the
  price of being able to say "I don't have anything on that" and mean it.
- **Cost: a rebuild takes about two minutes and spends free-tier quota.** Four
  batched requests, thirty seconds apart. Sent back to back they return 429:
  the binding free-tier limit counts tokens per minute and Google publishes no
  number for it, so the gap is measured rather than derived.
- **Cost: brute force is O(n) per query and will not stay free forever.** At 135
  chunks it is invisible. At ten thousand it would be noticeable and at a hundred
  thousand it would be wrong — but the corpus is this project's own
  documentation, which has a natural ceiling well below that.
- `docs/audits/` is excluded from the corpus and `assistant/index.py` says so in
  its module docstring, so that adding it back is a decision rather than an
  oversight. Audits are point-in-time snapshots, several already superseded; an
  assistant citing a 23 August audit as current would tell a panel that fixed
  bugs are still open.
- `docs/lanes/*.md` is also excluded — a judgement call, recorded in the same
  place. All four briefs open with near-identical "The project" and "Who owns
  what" sections that would crowd a five-result window with paraphrases of
  `docs/CONTEXT.md`'s canonical opening, and most of their remaining length is
  dated deliverable schedules rather than design.

## Alternatives considered

- **pgvector in the existing Postgres.** Genuinely on the table: Postgres is
  already in `docker-compose.yml`, so this is an extension rather than a new
  service. Rejected because it buys nothing at this scale — an index scan over
  135 rows is not faster than 135 dot products in Python — while adding a
  migration, a table, a connection at query time, and a dependency on the
  database being up for the assistant to answer a question about a *document*.
  It also puts a database import inside a package whose whole claim is that it is
  a library over static files (`assistant/tests/test_import_boundary.py`).
- **Chroma or FAISS in-process.** No deployment to add, so the ADR-0008 argument
  does not bite. Rejected on dependency weight: FAISS brings a native wheel and
  Chroma brings a small dependency tree, both to accelerate a loop that takes
  microseconds. `numpy` was rejected for the same reason — it is the right tool
  for 100,000 vectors and unjustifiable for 135.
- **Embedding at request time, with no committed index.** Simplest possible
  implementation: chunk the docs on startup, embed, hold in memory. Rejected
  because it makes the first request of every process spend four batched API
  calls and two minutes of free-tier quota, which is the failure `python -m
  governance.record` already exists to prevent — and because an in-memory index
  cannot be reviewed, diffed, or checked for staleness in CI.
- **Keyword search (BM25 or Postgres full-text).** No embedding call, no API key,
  no quota, and it would answer "what is the cooldown for" perfectly well.
  Rejected because it answers the *literal* questions and this assistant is asked
  conceptual ones: "what stops the LLM from raising a limit on its own" shares no
  content words with ADR-0003's `Decision` section, which is the correct answer
  and which the embedding index returns at 0.748. Worth reconsidering as a hybrid
  if a future question misses for a reason a keyword would have caught.
- **Fixed-size chunks with overlap.** The standard recipe, and it removes the
  need to parse markdown. Rejected because this corpus is unusually
  well-structured — every ADR has the same four headings, and those headings mark
  exactly the units an answer wants to quote. Throwing that away to re-derive it
  with a sliding window would be discarding the most reliable signal in the input.
