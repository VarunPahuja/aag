"""Build, load and search the documentation index.

THE CORPUS
----------
    docs/SYSTEM-EXPLAINED.md    the design and the glossary
    docs/CONTEXT.md             the system as it actually is, including what is missing
    docs/adr/*.md               every ADR except the template
    shared/reason_codes.py      each code with its human-readable sentence

The ADRs are the highest-value source and the reason this index exists. A question
about drift detection should come back with ADR-0006's actual argument — a cheap
tripwire first, a z-test only on what survives it — not with a paraphrase assembled
from the model's general knowledge of drift detection.

`docs/audits/` IS DELIBERATELY EXCLUDED, AND MUST STAY EXCLUDED. Audits are
point-in-time snapshots. Several are already wrong — they describe counts, gaps and
open bugs that were fixed weeks ago — and they are *supposed* to be wrong, because
their value is being a record of what was true on the day they were written. An
assistant quoting a 23 August audit as the current state of the system is not slightly
out of date; it is confidently telling a panel that fixed bugs are still open. If you
want audit history searchable, that is a different index with a date attached to every
answer, not two more globs in this list.

`docs/lanes/*.md` IS ALSO EXCLUDED, and this one was a judgement call. The lane briefs
are authoritative for their owners and they do carry real content — the hard rules, the
mode definitions. But all four open with a near-identical "The project" and "Who owns
what", which would put four paraphrases of `docs/CONTEXT.md`'s opening into the corpus
to compete with the canonical one; and most of their remaining length is per-lane
deliverable schedules, dated task lists, and "instructions for the AI assistant reading
this" — process, not design. Four near-duplicate chunks crowding a five-result window
costs more than the unique content buys. The unique content is mostly restated in
`docs/CONTEXT.md` and the ADRs anyway. Revisit if a real question misses because of it.

STALENESS
---------
Every source's SHA-256 is stored with its chunks, and `load_index()` warns loudly when
one has changed, been added, or been removed since the build. This lane has had this
exact bug once already: a prompt edited in place without a version bump replayed the
old wording and looked perfectly healthy, which is why `RecordingStaleError` exists. An
index that answers from a paragraph the repository no longer contains is the same
failure with a different file extension.

It warns rather than raising, which is the one place this differs from recordings. A
stale recording is *wrong* — it is the output of a prompt that no longer exists. A
stale index is merely *behind*: the chunks it holds were real text, and most of them
are still current. Refusing to answer at all would be a worse trade than answering with
a warning that says exactly which files moved. `strict=True` raises for callers (CI,
the `check` command) that would rather fail.
"""

from __future__ import annotations

import hashlib
import json
import warnings
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from assistant.chunking import Chunk, chunk_file, chunk_markdown
from assistant.embed import Embedder, build_embedder, cosine

# assistant/index.py -> repo root
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INDEX_PATH = Path(__file__).resolve().parent / "index.json"

SCHEMA_VERSION = "1"

REASON_CODES_SOURCE = "shared/reason_codes.py"

# Below this, a top result is not an answer. Measured against the real index rather
# than chosen by taste, on 14 Sept 2026:
#
#   five questions the docs do answer   best score 0.702 - 0.761
#   four questions they do not          best score 0.510 - 0.575
#     ("how do I bake sourdough bread", "what is our Kubernetes ingress
#      configuration", "who won the 2024 cricket world cup", "how do I rotate the
#      TLS certificate on the load balancer")
#
# Nothing landed between 0.575 and 0.702. 0.62 sits in that gap: 0.045 above the
# best false match, 0.082 below the weakest real answer.
#
# Note that the gap is a property of the *embedding dimensionality*, not just of the
# corpus: truncating the same vectors to 256 dimensions narrows it to 0.065 and to 128
# dimensions to 0.059, with the off-topic questions scoring 0.75-0.78 — everything
# drifts up together and the threshold stops being able to separate anything. That is
# why this index is 768-dimensional and 1.2 MB rather than a quarter of the size.
#
# It is a floor on *usefulness*, not a confidence score. A caller that gets nothing
# above it should say it has nothing on the subject. That is the entire point: the
# failure this index exists to avoid is answering a question about a system it has no
# text about, fluently, from a chunk that shares three words with the question.
#
# Nine probes is not a benchmark. Treat this as a working number with the evidence
# written down, and move it if a real question misses — but move it on a measurement.
RELEVANCE_THRESHOLD = 0.62

# Vectors are rounded before they are written. Six decimals is far below the noise
# floor of a 768-dimensional unit vector (each component is order 1e-2) and it is what
# the file can afford: dropping to five saves under 10% of the file and does change the
# ranking, because several correct chunks from the same ADR sit within 0.003 of each
# other and a coarser vector reorders them. Cheap precision, stable output.
VECTOR_PRECISION = 6

# A normalised vector whose norm has drifted further than this is not from this
# pipeline. Checked once at load, so `cosine()` can stay a bare dot product.
_NORM_TOLERANCE = 1e-3


class IndexStaleWarning(UserWarning):
    """A source file has changed since the index was built."""


class IndexStaleError(RuntimeError):
    """The same condition, for a caller that asked to fail instead of warn."""


@dataclass(frozen=True, slots=True)
class SearchResult:
    """One chunk and how well it matched.

    The score is here rather than on `Chunk` on purpose. A chunk is an index-time
    object — the same one is returned for many different queries — and a similarity is
    a property of a *pair*. Hanging a query-time number on a shared object is how a
    cached chunk ends up reporting the score from somebody else's question.
    """

    chunk: Chunk
    score: float

    @property
    def is_relevant(self) -> bool:
        return self.score >= RELEVANCE_THRESHOLD

    @property
    def citation(self) -> str:
        return self.chunk.citation


@dataclass(frozen=True, slots=True)
class Index:
    """Chunks, their vectors, and the fingerprints of the files they came from."""

    chunks: tuple[Chunk, ...]
    vectors: tuple[tuple[float, ...], ...]
    #: repo-relative POSIX path -> SHA-256 of the file's bytes at build time.
    sources: dict[str, str]
    embedding_model: str
    dimensions: int
    built_at: str
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if len(self.chunks) != len(self.vectors):
            raise ValueError(
                f"index has {len(self.chunks)} chunks and {len(self.vectors)} vectors; "
                f"they are paired by position, so a mismatch misattributes citations."
            )

    def to_json(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "built_at": self.built_at,
            "embedding_model": self.embedding_model,
            "dimensions": self.dimensions,
            "sources": dict(sorted(self.sources.items())),
            "chunks": [
                {**chunk.to_json(), "vector": list(vector)}
                for chunk, vector in zip(self.chunks, self.vectors, strict=True)
            ],
        }

    @classmethod
    def from_json(cls, payload: dict, *, source: Path | None = None) -> Index:
        where = source.name if source else "index payload"
        found = payload.get("schema_version")
        if found != SCHEMA_VERSION:
            raise ValueError(
                f"{where} has schema_version {found!r}, this code reads {SCHEMA_VERSION!r}. "
                f"Rebuild with: python -m assistant build"
            )
        entries = payload["chunks"]
        return cls(
            chunks=tuple(Chunk.from_json(entry) for entry in entries),
            vectors=tuple(tuple(float(v) for v in entry["vector"]) for entry in entries),
            sources=dict(payload["sources"]),
            embedding_model=payload["embedding_model"],
            dimensions=int(payload["dimensions"]),
            built_at=payload["built_at"],
            schema_version=found,
        )


# ---------------------------------------------------------------------------------
# Corpus
# ---------------------------------------------------------------------------------


def corpus_files(root: Path | None = None) -> list[Path]:
    """Every markdown file in the corpus, in a stable order.

    `0000-template.md` is skipped: it is a form, not a decision, and its headings are
    the same ones every real ADR has, so it is a chunk-for-chunk near-duplicate of
    nothing in particular.
    """
    root = root or REPO_ROOT
    files = [root / "docs" / "SYSTEM-EXPLAINED.md", root / "docs" / "CONTEXT.md"]
    files += [p for p in sorted((root / "docs" / "adr").glob("*.md")) if p.name != "0000-template.md"]
    missing = [p for p in files if not p.is_file()]
    if missing:
        raise FileNotFoundError(
            "corpus file(s) missing: " + ", ".join(p.as_posix() for p in missing)
        )
    return files


def build_chunks(root: Path | None = None) -> list[Chunk]:
    """Every chunk in the corpus, markdown and reason codes together."""
    root = root or REPO_ROOT
    chunks: list[Chunk] = []
    for path in corpus_files(root):
        chunks.extend(chunk_file(path, root=root))
    chunks.extend(reason_code_chunks(root))
    return chunks


def reason_code_chunks(root: Path | None = None) -> list[Chunk]:
    """One chunk per reason code: the code, its category, and its sentence.

    Rendered to markdown and put through the same chunker as everything else, so there
    is one splitting path rather than two. The categories come from the section
    comments in the file itself (`# --- why an increase was blocked ---`), which is
    real grouping a reader put there.

    The sentences are read from `HUMAN_READABLE` by importing it, not by copying it.
    `shared/reason_codes.py` is a treaty file and the rule is that the human sentence
    is generated *from* the code; an index with its own second copy of those strings
    would be a place for them to drift.
    """
    root = root or REPO_ROOT
    source = (root / REASON_CODES_SOURCE).read_text(encoding="utf-8")
    human_readable = _human_readable(root)

    lines = ["# Reason codes (`shared/reason_codes.py`)", ""]
    lines += [
        "Machine-readable reasons attached to every evaluation. The backend renders",
        "them, the frontend styles them, and governance agents read them. The human",
        "sentence is generated from the code, never the other way round. Append-only:",
        "renaming a code silently breaks whatever reads it.",
        "",
    ]
    for category, code in _codes_by_category(source):
        sentence = human_readable.get(code)
        if sentence is None:
            continue
        lines += [f"## {category}: {code}", "", f"`{code}` — {sentence}", ""]

    return chunk_markdown("\n".join(lines), source=REASON_CODES_SOURCE)


def _human_readable(root: Path) -> dict[str, str]:
    """`shared.reason_codes.HUMAN_READABLE`, imported rather than re-parsed."""
    import sys

    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from shared.reason_codes import HUMAN_READABLE

    return dict(HUMAN_READABLE)


def _codes_by_category(source: str) -> list[tuple[str, str]]:
    """Walk the source, pairing each constant with the `# --- ... ---` above it."""
    pairs: list[tuple[str, str]] = []
    category = "reason code"
    for line in source.splitlines():
        stripped = line.strip()
        if stripped.startswith("# ---") and stripped.endswith("---"):
            heading = stripped.strip("#- ").strip()
            if heading:
                category = heading
            continue
        if ": Final = " in stripped and not stripped.startswith("HUMAN_READABLE"):
            name = stripped.split(":", 1)[0].strip()
            if name.isupper():
                pairs.append((category, name))
    return pairs


def source_digest(path: Path) -> str:
    """SHA-256 of a file's content, with line endings normalised to `\\n` first.

    **Not the raw bytes, and that is not a convenience.** The obvious implementation
    hashes `path.read_bytes()` and it makes the staleness guard fire on every file in
    CI: this index is built on Windows, `.gitattributes` says `eol=lf`, and the same
    document is therefore CRLF in one working tree and LF in another. A guard that
    cries stale on every Linux checkout is a guard that gets switched off.

    Normalising is also the honest comparison. The question this digest answers is
    "would rebuilding produce different chunks?", and `str.splitlines()` discards the
    carriage returns before any of them reach a chunk. A file whose only change is its
    line endings genuinely has nothing new to embed.
    """
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def source_digests(root: Path | None = None) -> dict[str, str]:
    """The fingerprint of every corpus file, keyed by repo-relative POSIX path."""
    root = root or REPO_ROOT
    paths = [*corpus_files(root), root / REASON_CODES_SOURCE]
    return {p.resolve().relative_to(root.resolve()).as_posix(): source_digest(p) for p in paths}


# ---------------------------------------------------------------------------------
# Build / save / load
# ---------------------------------------------------------------------------------


def build_index(
    root: Path | None = None,
    *,
    embedder: Embedder | None = None,
    previous: Index | None = None,
) -> Index:
    """Chunk the corpus and embed every chunk. Makes network calls.

    Deliberately not something that happens on import or on a first search. Building is
    an act with a quota attached and an artifact to review; replay is the thing that has
    to be instant, and a lazy build would put its network calls in front of whoever is
    watching the demo. Same reasoning as `python -m governance.record`.

    **`previous` makes the build incremental, and the free tier makes that necessary.**
    Gemini's `embed_content_free_tier_requests` quota counts *contents*, not requests —
    1,000 a day, so roughly seven full builds — and a day of iterating on the chunker
    exhausts it. Editing one ADR should cost the five chunks that changed, not all 135.
    A chunk is reused when the exact text that was embedded is unchanged, which is the
    only safe key: it is what produced the vector.

    Reuse is refused outright when the previous index came from a different model or
    dimensionality, because a file mixing two embedding spaces would still load, still
    search, and return nonsense that looks like a number.
    """
    root = root or REPO_ROOT
    embedder = embedder or build_embedder()
    chunks = build_chunks(root)

    reusable = _reusable_vectors(previous, embedder)
    fresh = [chunk for chunk in chunks if chunk.embedding_text not in reusable]
    embedded = embedder.embed_documents([chunk.embedding_text for chunk in fresh])
    if len(embedded) != len(fresh):
        raise ValueError(f"embedder returned {len(embedded)} vectors for {len(fresh)} chunks")

    minted = dict(zip([c.embedding_text for c in fresh], embedded, strict=True))
    vectors = [reusable.get(c.embedding_text) or minted[c.embedding_text] for c in chunks]
    return Index(
        chunks=tuple(chunks),
        vectors=tuple(tuple(round(v, VECTOR_PRECISION) for v in vector) for vector in vectors),
        sources=source_digests(root),
        embedding_model=embedder.model,
        dimensions=embedder.dimensions,
        built_at=datetime.now(UTC).isoformat(timespec="seconds"),
    )


def _reusable_vectors(previous: Index | None, embedder: Embedder) -> dict[str, list[float]]:
    """Embedded text -> its vector, for chunks a previous build already paid for."""
    if previous is None:
        return {}
    if (previous.embedding_model, previous.dimensions) != (embedder.model, embedder.dimensions):
        return {}
    return {
        chunk.embedding_text: list(vector)
        for chunk, vector in zip(previous.chunks, previous.vectors, strict=True)
    }


def save_index(index: Index, path: Path | None = None) -> Path:
    """Write the committed artifact."""
    path = path or DEFAULT_INDEX_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    # `newline="\n"` explicitly: the default on Windows writes CRLF, `.gitattributes`
    # stores this file as LF, and the difference is a whole-file diff on every rebuild
    # from the wrong machine.
    path.write_text(dumps(index), encoding="utf-8", newline="\n")
    return path


def dumps(index: Index) -> str:
    """Serialise the index: indented structure, but each vector on one line.

    Hand-rolled rather than `json.dumps(..., indent=1)` because that puts every one of
    a hundred thousand floats on a line of its own and makes the file half again as
    large for nothing.
    The indentation is worth keeping for everything else — `sources` and each chunk's
    `source`, `heading_path` and `text` are the parts a reviewer actually reads, and
    they should diff a line at a time when a document changes. Nobody reads a vector,
    so a vector gets one line.

    `json` does the escaping throughout; this only decides where the newlines go.
    """
    payload = index.to_json()
    out = ["{"]
    for key in ("schema_version", "built_at", "embedding_model", "dimensions"):
        out.append(f' "{key}": {json.dumps(payload[key])},')

    out.append(' "sources": {')
    sources = list(payload["sources"].items())
    for position, (name, digest) in enumerate(sources):
        tail = "," if position < len(sources) - 1 else ""
        out.append(f"  {json.dumps(name)}: {json.dumps(digest)}{tail}")
    out.append(" },")

    out.append(' "chunks": [')
    entries = payload["chunks"]
    for position, entry in enumerate(entries):
        tail = "," if position < len(entries) - 1 else ""
        out.append("  {")
        out.append(f'   "source": {json.dumps(entry["source"], ensure_ascii=False)},')
        out.append(f'   "heading_path": {json.dumps(entry["heading_path"], ensure_ascii=False)},')
        out.append(f'   "part": {json.dumps(entry["part"])},')
        out.append(f'   "text": {json.dumps(entry["text"], ensure_ascii=False)},')
        out.append(f'   "vector": {json.dumps(entry["vector"])}')
        out.append(f"  }}{tail}")
    out.append(" ]")
    out.append("}")
    return "\n".join(out) + "\n"


def load_index(
    path: Path | None = None,
    *,
    root: Path | None = None,
    strict: bool = False,
    check_sources: bool = True,
) -> Index:
    """Read the committed index, complaining loudly if the docs have moved under it.

    `check_sources=False` is for a caller holding an index built from somewhere other
    than this repository — a test fixture, mostly. Everything else should let it check.
    """
    path = path or DEFAULT_INDEX_PATH
    if not path.is_file():
        raise FileNotFoundError(
            f"no index at {path}. Build it with: python -m assistant build"
        )
    index = Index.from_json(json.loads(path.read_text(encoding="utf-8")), source=path)
    _check_norms(index, path)
    if check_sources:
        report_staleness(index, root=root, strict=strict)
    return index


def stale_sources(index: Index, *, root: Path | None = None) -> dict[str, str]:
    """Which corpus files disagree with the index, and how. Empty means current."""
    current = source_digests(root or REPO_ROOT)
    problems: dict[str, str] = {}
    for name, digest in sorted(current.items()):
        if name not in index.sources:
            problems[name] = "not in the index — it was added after the build"
        elif index.sources[name] != digest:
            problems[name] = "changed since the build"
    for name in sorted(index.sources):
        if name not in current:
            problems[name] = "in the index but no longer in the corpus"
    return problems


def report_staleness(index: Index, *, root: Path | None = None, strict: bool = False) -> None:
    """Warn (or raise) about every source that has moved since the build."""
    problems = stale_sources(index, root=root)
    if not problems:
        return
    detail = "\n".join(f"  {name}: {why}" for name, why in problems.items())
    message = (
        f"assistant/index.json was built {index.built_at} and no longer matches the "
        f"documentation it indexes:\n{detail}\n"
        f"Answers may quote text this repository no longer contains. "
        f"Rebuild with: python -m assistant build"
    )
    if strict:
        raise IndexStaleError(message)
    warnings.warn(message, IndexStaleWarning, stacklevel=3)


def _check_norms(index: Index, path: Path) -> None:
    """Every stored vector must be unit length, because `cosine()` assumes it.

    Sampled rather than exhaustive: the vectors come out of one pipeline, so either all
    of them are normalised or none are, and checking a few hundred dot products on
    every load to prove something the writer guaranteed is a cost with no reader.
    """
    for position in range(0, len(index.vectors), max(1, len(index.vectors) // 8 or 1)):
        vector = index.vectors[position]
        if len(vector) != index.dimensions:
            raise ValueError(
                f"{path.name}: chunk {position} has {len(vector)} dimensions, header "
                f"says {index.dimensions}."
            )
        norm = sum(value * value for value in vector) ** 0.5
        if abs(norm - 1.0) > _NORM_TOLERANCE:
            raise ValueError(
                f"{path.name}: chunk {position} has norm {norm:.6f}, not 1.0. Cosine "
                f"similarity is computed as a plain dot product and would be wrong."
            )


# ---------------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------------


def search_vector(index: Index, query_vector: list[float], k: int = 5) -> list[SearchResult]:
    """The top `k` chunks for an already-embedded query. Pure — no I/O at all.

    Ties break on source, heading path and part, so two chunks with the same score come
    back in the same order on every machine and every run. Float arithmetic over the
    same inputs is deterministic; the *order* of equal scores is not, unless it is made
    to be.
    """
    if k <= 0:
        return []
    scored = [
        SearchResult(chunk=chunk, score=cosine(list(vector), query_vector))
        for chunk, vector in zip(index.chunks, index.vectors, strict=True)
    ]
    scored.sort(key=lambda r: (-r.score, r.chunk.source, r.chunk.heading_path, r.chunk.part))
    return scored[:k]


def search(
    index: Index,
    query: str,
    k: int = 5,
    *,
    embedder: Embedder | None = None,
) -> list[SearchResult]:
    """Embed `query` and return the top `k` chunks with their scores.

    One network call, for the query. Everything after it is arithmetic over the loaded
    index — no per-chunk requests, no database, nothing to stand up.

    **The score comes back, always, and is not filtered here.** A caller that wants
    "I don't have anything on that" needs to see *how* weak the best match was; a
    search that silently returned an empty list would look identical to a search that
    found nothing at all, and the two want different answers. `SearchResult.is_relevant`
    compares against `RELEVANCE_THRESHOLD` for callers that just want the verdict.
    """
    embedder = embedder or build_embedder()
    return search_vector(index, embedder.embed_query(query), k)
