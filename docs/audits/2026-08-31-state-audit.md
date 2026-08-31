# State Audit — 2026-08-31

Read-only. Nothing in this repository was written, edited, staged, committed,
pushed, merged, rebased, deleted, or formatted to produce this report except
this file itself. Verification (`pytest`, `ruff`, `npm run typecheck`,
`docker compose config`) was run either directly against a read-only checkout
or inside disposable `git worktree`s / clean `.venv`s created outside the
tracked repository and removed afterward. `git status` on the actual working
tree was not touched by any of this.

Baseline: `docs/audits/2026-08-27-delta-audit.md`. This audit answers: what
changed since, does it hold up, and are we going to make 15 September.

Also read as ground truth: `docs/audits/2026-08-23-state-audit.md`,
`docs/audits/2026-08-23-port-feasibility.md`, `docs/DEADLINES.md`,
`docs/CONTEXT.md`, `docs/RISKS.md`, all 15 files in `docs/adr/`, all four
`docs/lanes/*.md`.

Mid-audit addendum, added on the user's instruction after Task 3 was
underway: verify specific third-party tooling claims (statsmodels, Hypothesis,
Recharts, shadcn/ui, tenacity, respx, pytest-httpx), and re-investigate
`origin/vc/gemini-client`/`origin/vc/swappable-providers` under new
information — **swappable LLM providers is now confirmed in scope: the team
is moving to Azure OpenAI as the primary provider with Gemini as fallback.**
This supersedes this audit's own initial framing of that work as
undecided/possible-scope-creep; see §1 and the addendum in §3.

---

## 2. `shared/` integrity — reported first, per instructions

**No file under `shared/` was modified on any branch since the freeze.**
Verified directly (not delegated) with `git diff origin/main...<branch> --
shared/ --stat` against every branch with commits since 27 Aug or still
outstanding: `origin/vc/prompts-and-cached-mode`, `origin/vc/gemini-client`,
`origin/vc/swappable-providers`, `origin/uk/autonomy-ladder`,
`origin/ad/simulator-frontend`, `origin/vc/langgraph-skeleton`,
`origin/uk/trust`, `origin/uk/shared-trust-contracts`, `origin/vc/governance`
— every diff is empty. `git log --since=2026-08-27 --oneline -- shared/`
against `main` itself also returns nothing. **No stop-the-line finding. The
freeze held completely.**

### Local types duplicating a shared one — checked for a third/fourth instance

- **`trust/` — clean.** `ScoreResult` remains fully retired (`grep -rn
  "ScoreResult" trust/` → zero hits, confirmed again this audit).
  `LadderResult` (`trust/trust_engine/ladder.py:57-63`) is a 5-field internal
  dataclass, unpacked 1:1 into `TrustEvaluation` inside `evaluate.py` and
  never returned to a caller outside `trust_engine` — not a rival public
  contract.
- **`governance/` — clean.** PR #15/#16 added a new `governance/llm/`
  subpackage (`LLMClient` protocol, `GeminiConfig`/`ClaudeConfig`/
  `OpenAIConfig`, `GeminiClient`/`ClaudeClient`/`OpenAIClient`, `Recording`/
  `RecordingStore`, seven error classes). None of `governance/llm/*.py`
  imports from `shared/` at all (`grep -rn "from shared\|import shared"
  governance/governance/llm/` → zero hits) — these are HTTP-transport-layer
  types with no `shared/` equivalent, legitimately lane-local infrastructure.
- **`simulator/`/`frontend/` — nothing to check.** `git log --since=2026-08-27
  --name-status -- simulator/ frontend/` shows exactly one commit in the
  window (`c4c09a2`), and it is delete-only plus two small edits — zero new
  files added to either directory since 27 Aug.
- **`backend/`** (PR #17) mirrors `shared/contracts.py` fields into SQLAlchemy
  ORM models (`backend/app/models/*.py`) — this is the documented,
  intentional pattern (ADR-0013: "mirror field-for-field rather than
  inventing a parallel shape"), not a competing public contract; DB rows and
  frozen dataclasses serve different jobs by design.

**No third structural-duplicate-type instance found anywhere since 27 Aug.**

### A second reason-code vocabulary — flagged, but ADR-documented and intentional

`backend/app/policy/reason_codes.py` is a second vocabulary, separate from
`shared/reason_codes.py`'s 18 codes — six new codes (`WITHIN_LIMIT`,
`LIMIT_EXCEEDED`, `AGENT_SUSPENDED`, `AGENT_RESTRICTED`,
`POLICY_VERSION_MISSING`, `POLICY_VERSION_INVALID`), all `POLICY_`-prefixed
specifically to prevent collision if promoted into `shared/` later. This is
exactly what the audit brief asked to flag ("a second set of reason codes"),
and it is not a violation: ADR-0014 documents the decision, the reason given
(`shared/reason_codes.py`'s 18 existing codes describe *why the autonomy
ladder moved*, none describe *why one decision was allowed or escalated* —
a different question) is sound, and `shared/` is frozen so adding to it
unilaterally would itself have been the violation. Flagged for visibility,
not as a defect.

---

## 1. What moved since 27 August

All 19 PRs opened to date show `state: MERGED` in `gh pr list --state all`.
**Zero open PRs exist right now.**

### Merged into `main` since the 27 Aug baseline (baseline tip was `1c125af`, PR #6)

| PR | Branch | Merge commit | Merged at | Author | Files / lines | What it shipped |
|---|---|---|---|---|---|---|
| #7 | `uk/autonomy-ladder` | `88871e8` | 2026-08-27 11:50 | Varun Pahuja | 6 files, +605/-38 | `evaluate()`, ladder, `ScoreResult` retired (real merge, ancestor of `main`) |
| #8 | `ad/simulator-frontend` | `4f0af61` | 2026-08-27 11:51 | Varun Pahuja | 17 files (port) + `c4c09a2` cleanup | Simulator ported onto frozen contracts, duplicate Wilson deleted, `nexttemp/` dropped, `agents/llm.py` removed |
| #9 | `docs/resurrect-pr5` | `075b56d` | 2026-08-27 11:49 | Varun Pahuja | `docs/SYSTEM-EXPLAINED.md` | Recovered PR #5's stranded content |
| #10 | `docs/delta-audit-27aug` | `1bf281e` | 2026-08-27 11:54 | Varun Pahuja | this audit's own baseline file | 27 Aug delta audit |
| #11 | `vp/openapi-contract` | `a9af693` | 2026-08-27 12:55 | Varun Pahuja | `backend/app/main.py` + 18 stub endpoints, `backend/openapi.json` | **First real backend code** — 2 days late vs. the 25 Aug date |
| #12 | `vc/prompts-and-cached-mode` | `43191e7` | 2026-08-28 06:48 | Varun Chaurasia | `governance/prompts/*`, 54 new tests | Versioned prompts, evidence rendering, Gemini-dialect schema (real, non-squash merge) |
| #13 | `docs/mentor-briefing` | `6259e6e` | 2026-08-28 06:53 | Varun Pahuja | `interactivehtml/*` | Mentor briefing page |
| #14 | `docs/landscape-research` | `5fc4691` | 2026-08-29 18:13 | Varun Pahuja | `docs/research/*`, `interactivehtml/index.html` | Prior-art review |
| #15 | `vc/gemini-client` | `c7b82d4` | 2026-08-29 18:13 | Varun Chaurasia | 13 files, +1,431/-20 | Gemini HTTP client, recording store, working cached-mode plumbing |
| #16 | `vc/swappable-providers` | `277a234` | 2026-08-30 17:04 | Varun Chaurasia | 17 files, +1,503/-173 | Claude/OpenAI clients, `GOVERNANCE_PROVIDER` registry, ADR-0012 |
| #17 | `vp/schema-and-policy-engine` | `b1ba3d0` | 2026-08-31 09:52 | Varun Pahuja | 40 files, +3,732 | SQLAlchemy models, Alembic migration, seed script, Policy Engine as a pure module |
| #18 | `vp/schema-and-policy-engine` (2nd) | `7ee67d5` | 2026-08-31 10:31 | Varun Pahuja | `recommendations.generated_at` column | Fixed a schema gap flagged in PR review |
| #19 | `chore/branch-cleanup-31aug` | `0ad103a` | 2026-08-31 10:36 | Varun Pahuja | `docs/DECISION_LOG.md` | Logged 31 Aug branch cleanup |

**Content-verified, not just ancestry-checked**: #7, #9, #10, #11, #12 are real
(non-squash) merges — their branch tips are literal ancestors of `main`. #8,
#13, #14, #15, #16, #17, #18, #19 are squash merges — each verified by
diffing the branch's own touched files against the exact squash commit that
closed it; every diff is empty.

**Total non-merge commits since 27 Aug 00:00: 22**, spanning `docs/`,
`governance/`, `backend/`, and one `trust/` style-only fix
(`091bdf6`, import ordering, no logic change, self-confirmed by an unchanged
174-test count).

### Every branch still open on `origin` — finished or abandoned?

| Branch | Tip | Date | Status | Assessment |
|---|---|---|---|---|
| `origin/vc/prompts-and-cached-mode` | `5e34372` | 27 Aug | Merged (real merge, PR #12) | Finished, superseded by #15/#16 in the same files |
| `origin/vc/gemini-client` | `a150262` | 29 Aug | Merged (squash, PR #15) | Finished — see below |
| `origin/vc/swappable-providers` | `a929636` | 30 Aug | Merged (squash, PR #16) | Finished — see below |
| `origin/uk/autonomy-ladder` | `091bdf6` | 27 Aug | Merged (real merge, PR #7) | Finished |
| `origin/ad/simulator-frontend` | `c4c09a2` | 27 Aug | Merged (squash, PR #8) | Finished but incompletely cleaned (see §4) |
| `origin/vc/langgraph-skeleton`, `origin/uk/trust`, `origin/uk/shared-trust-contracts`, `origin/vc/governance` | — | ≤26 Aug | Long-merged / scaffold | Unchanged, out of this window |

No branch in scope is abandoned. All work either merged or is superseded by
later work in the same files. `origin/vp/backend`, `origin/vc/governance`,
`origin/ad/simulator-frontend`, `origin/uk/trust` local refs remain stuck at
the 17 Aug scaffold commit (`c126543`) — harmless, their real work landed
under differently-named branches, matching the pattern the 27 Aug audit
already noted for `vp/backend`/`vc/governance`.

### `origin/vc/gemini-client` and `origin/vc/swappable-providers` — investigated in depth, then re-investigated under new information

Neither branch appears in `docs/DEADLINES.md` by name — the sheet names only
"Sun 30 Aug — VC — Prompt files, structured output parsing, cached mode" and
"Thu 3 Sept — VC — Live mode behind a flag, timeout, fallback to cached."

**Size and content.** PR #15 (`c7b82d4`): 13 files, +1,431/-20 —
`governance/llm/gemini.py` (277 lines), `recording.py` (185),
`errors.py` (83), `record.py` (137, a CLI recording tool),
`scenarios.py` (187, five representative `TrustEvaluation` scenarios),
`agents/llm_backed.py` (56), `tests/test_llm.py` (407 new tests). PR #16
(`277a234`): 17 files, +1,503/-173 — adds `claude.py` (201),
`openai_client.py` (186), `registry.py` (117), `docs/adr/0012-...md` (123),
`tests/test_providers.py` (389 new tests); rewrites `gemini.py` (-98 net) to
fit the shared `LLMClient` protocol and fixes a cache-key bug (the key now
includes the model — `governance/governance/llm/recording.py:cache_key_for()`
— previously it did not, which would have silently replayed one provider's
recording for another's request). 193 governance tests total, matching PR
#16's own commit message ("193 governance tests, was 160") and
`docs/CONTEXT.md:207`'s 29 Aug figure exactly.

**Does it duplicate #6/#12's work?** No file-level overlap — `governance/llm/`
is new; `governance/prompts/` (PR #12) is untouched except `prompts/schema.py`
gaining the two new JSON-Schema dialects. No structural type duplication (see
§2 above).

**Original framing (pre-addendum): unresolved scope.** `docs/adr/0012-
swappable-llm-providers-for-panel-independence.md:5` reads **`Status:
Proposed`**, explicitly stating it "needs a decision from the team" because
`docs/lanes/vc.md` says "Do not introduce any paid API or service" and
Claude/OpenAI are paid. `grep -in "0012\|swappable\|provider\|paid api"
docs/DECISION_LOG.md` returns **zero hits** — no record anywhere that the
team discussed or ruled on this before PR #16 merged to `main` on 30 Aug.
`docs/CONTEXT.md:207` itself says "See ADR-0012, which asks the team to rule
on the paid-API constraint" — still unresolved in the docs as of this audit.

**Superseding information, mid-audit**: the user confirmed the team has since
decided to move to **Azure OpenAI as primary, Gemini as fallback** — this
resolves the open ADR-0012 question in practice, even though nothing in the
repository reflects that decision yet (`grep -in azure` across the entire
repo: **zero hits**, anywhere — not in code, not in the ADR, not in
`docs/DECISION_LOG.md`, not in `docs/CONTEXT.md`).

**Is the merged code positioned to support that plan? Partially — the
abstraction is ready, the specific client and the fallback mechanism are
not.**

- `governance/governance/llm/openai_client.py:136`:
  `return openai.OpenAI(api_key=self.config.api_key, timeout=self.config.timeout_s)`
  — the SDK's plain `OpenAI` client, **not** `AzureOpenAI`. `OpenAIConfig`
  has no `azure_endpoint`, `api_version`, or deployment-name field; routing
  is by model-name string, which is not how Azure OpenAI addresses models
  (Azure routes by a deployment name you configure, and needs a distinct
  SDK client class and auth shape).
- `governance/governance/llm/registry.py:41-45,39`: `_BUILDERS = {GEMINI:
  GeminiClient, CLAUDE: ClaudeClient, OPENAI: OpenAIClient}`, `DEFAULT_PROVIDER
  = GEMINI` — three providers only, no `"azure"` key anywhere.
- `LLMClient` (`governance/governance/llm/base.py:60-73`) is a minimal,
  four-member `Protocol` (`provider`, `model`, `generate(prompt) -> str`,
  `has_key`) — deliberately thin. Adding an `AzureOpenAIClient` implementing
  this same protocol is architecturally low-effort; the registry pattern,
  lazy-import convention, and cache-key-includes-model design all transfer
  directly. **The abstraction was built in a shape that supports this kind
  of extension — the specific client just doesn't exist yet.**
- **The larger gap: no primary/fallback concept exists at all.**
  `resolve_provider()` (`registry.py:62-80`) selects exactly **one** provider
  per agent by strict precedence (per-agent env var → global env var →
  default) — there is no "try A, fall back to B" logic anywhere in
  `governance/`. That behavior is scoped as the Thu 3 Sept live-mode
  deliverable, and live mode raises `NotImplementedError` unconditionally on
  every path today (see §3, governance). "Azure primary, Gemini fallback" as
  a *runtime failover* has no home to go into yet — today's registry can
  support "Azure as the new default" (flip `DEFAULT_PROVIDER`) but not
  "Azure with automatic fallback to Gemini on failure."

**Direct verdict**: the provider interface is well-positioned for this
change but **not complete enough today**. Three concrete pieces of work
remain, none built yet: (1) an `AzureOpenAIClient` class using the SDK's
`AzureOpenAI` client with `azure_endpoint`/`api_version`/deployment-name
config, registered in `registry.py`; (2) a decision on what "primary" means
in the registry (at minimum flipping `DEFAULT_PROVIDER`, naming the new
provider key); (3) the actual fallback mechanism itself, which is really the
substance of the already-scheduled Thu 3 Sept live-mode deliverable, not a
separate task. ADR-0012 should be updated to record the Azure decision and
move off `Status: Proposed` — right now the ADR that would carry this
decision doesn't mention it at all.

**Verdict on "does swappable providers represent scope nobody asked for"**:
superseded by the user's clarification — it does not. It anticipated
correctly (an abstraction was needed before anyone could plug in
Azure/Claude/OpenAI), even though the specific target provider hadn't been
named in `docs/DEADLINES.md` when it was built.

---

## 3. Deliverables against `docs/DEADLINES.md`

### Phase 1, 24–31 August — DONE / PARTIAL / MISSING against the sheet's own check

| Date | Who | Deliverable | Check (verbatim intent) | Status | Evidence |
|---|---|---|---|---|---|
| Mon 24 Aug | VC | Start `vc/langgraph-skeleton` | Branch exists with a commit | **DONE** | `c43fb64`, merged PR #6 (established prior audit, unchanged) |
| Mon 24 Aug | AD | Start `ad/simulator-port`, mapping posted | Mapping posted before code | **PARTIAL** | Code is a real port; work landed on `ad/simulator-frontend` not a branch named `ad/simulator-port`; no group-posted mapping found in repo (out-of-repo-scope, carried from 27 Aug baseline, not re-verifiable) |
| Tue 25 Aug | VP | `openapi.json` committed, staleness check verified | AD can generate types without asking | **DONE (2 days late)** | `backend/openapi.json` exists, 18 documented paths, PR #11 merged 27 Aug 12:55 |
| Wed 26 Aug | UK | `evaluate()`, ladder, cooldowns, clawback, `ScoreResult` retired | One call returns the full contract, 18 codes reachable | **DONE** | `trust/trust_engine/evaluate.py`/`ladder.py`, confirmed field-by-field this audit (§4) |
| Wed 26 Aug | VC | LangGraph skeleton, stub mode | Valid `Recommendation` from canned data, zero LLM calls | **DONE** | `governance/governance/coordinator.py`, confirmed this audit |
| Thu 27 Aug | AD | Simulator ported, fixtures regenerated, dup Wilson deleted | `pytest simulator/` green on `main`'s contracts | **DONE** on the port/Wilson; **fixtures-regenerated status not independently re-verified** this round (unchanged open question from 27 Aug baseline) | 97/97 tests, `runner.py:47` imports `wilson_lower_bound` from `trust/` |
| Fri 28 Aug | VP | Alembic migration, all tables, seed script | `make db-reset` produces a seeded DB | **DONE** | `backend/alembic/versions/0001_initial_schema.py`, `backend/app/seed.py`, `test_alembic_migration.py`/`test_seed.py` pass |
| Sat 29 Aug | VP | Policy Engine as a pure module + tests | Invoice + policy version → allow/escalate + reason code, no DB imports | **DONE** | `backend/app/policy/engine.py`, AST import-boundary test, Hypothesis property tests all confirmed real this audit (§4) |
| Sat 29 Aug | AD | Frontend types from `openapi.json`, hand-written types deleted, `nexttemp/` removed, `typecheck` added, `shadcn/ui` added | `npm run typecheck` clean, no hand-written types remain | **PARTIAL, 2 days late** | `nexttemp/` removed and `typecheck` added — **but both by Varun P.'s `c4c09a2`, not Adhya**. `frontend/src/types/api.ts:1-6` still says "TypeScript types mirroring shared/contracts.py Pydantic models" by hand; no codegen script exists anywhere in `frontend/package.json`; `shadcn/ui` absent from every dependency list, `frontend/components.json` doesn't exist |
| Sun 30 Aug | VC | Prompt files, structured output, cached mode, real Gemini responses recorded/replayed | Real responses recorded once, replayed deterministically | **PARTIAL** | Code is real and complete (`governance/governance/agents/llm_backed.py`, `RecordingStore`) — but `git ls-tree -r origin/main -- governance/recordings/` shows **exactly one file, `.gitkeep`**. Zero real recordings exist. `governance/tests/test_modes_and_agents.py:44-49`'s own test proves this: it asserts a `RecordingMissError` against the *default* store |
| Mon 31 Aug (today) | VP | Decision ingest, real persistence, hash-chained audit log | POST a decision, see it in the DB with a valid chain link | **MISSING** | `backend/app/api/v1/decisions.py:22-45`'s `create_decision()` mints a `DecisionRecordOut` from `app.fixtures.decisions.DECISIONS` and returns it — never opens a `Session`, never calls `evaluate_decision`, never calls `append_entry`. Two identical POSTs return two different ids and nothing changes in the fixture list. `docs/DECISION_LOG.md`'s own 2026-08-31 PR #17 entry confirms this was deliberately deferred: *"does not wire any API endpoint to the database — the stubs in `backend/app/api/v1/` are untouched; that is Mon 31 Aug / Thu 3 Sept work."* |

### Backend-specific checks, asked for directly

- **Does decision ingest exist?** A `POST /api/v1/decisions` route exists and
  is reachable. **Is anything actually persisted?** No — `backend/app/api/v1/`
  has zero occurrences of `Session`, `session.add`, or `session.commit`
  across all seven of its files (`agents.py`, `audit.py`, `decisions.py`,
  `health.py`, `pagination.py`, `recommendations.py`, `simulation.py`).
  Every handler reads/returns `app/fixtures/*.py` module-level data.
- **Is the audit chain appended to on real events, or unwired?**
  **Unwired.** `grep -rn "append_entry" backend/` returns only its own
  definition and its one call site, inside `backend/app/seed.py:867`. No API
  handler calls it. `app/models/audit_log.py:10-13`'s own docstring: "ingest
  wiring... lands later; this module is the primitive that wiring will
  call."
- **Is the Policy Engine wired into any request path?** No. `grep -rn
  "from app.policy\|import app.policy"` under `backend/app/api/` returns
  **zero hits**. `evaluate_decision`/`clamp_recommendation` are called only
  from `backend/app/seed.py` and `backend/tests/`. **It is a library nothing
  in the live request path calls**, exactly as literally as that phrase
  reads.

### Trust-specific checks

- `evaluate(decisions, context) -> TrustEvaluation` exists, `trust/
  trust_engine/evaluate.py:21`, merged on `main`.
- **Does it populate every field?** 26 of 28 `TrustEvaluation` fields are set
  explicitly (`evaluate.py:59-83`); the remaining two (`evaluated_at`,
  `config_fingerprint`) are correctly left at their dataclass defaults —
  `trust/` is barred from wall-clock reads, so it cannot legally stamp
  `evaluated_at` itself; both are stamped by the backend at write time
  (`backend/app/fixtures/trust.py:86-87`, `backend/app/seed.py:524-525`).
  Not a gap — a correct division of responsibility.
- **How many of 18 reason codes are reachable, one test each?** **15 of 18**
  inside `trust/`, each with a dedicated test (table verified this audit,
  file:line for every emission and test site). The remaining 3
  (`SAMPLE_EVIDENCE_INSUFFICIENT`, `RECOMMENDATION_CLAMPED`,
  `SAMPLE_REVIEW_DISAGREEMENT`) are correctly out of the trust lane's scope —
  `SAMPLE_EVIDENCE_INSUFFICIENT` is emitted by `governance/governance/agents/
  audit.py:22,34`; the other two are backend/governance concerns.
- **Is `ScoreResult` retired?** Yes, zero hits, unchanged since 26 Aug.

### Governance-specific checks

- **Does the graph run in cached mode with real recorded responses?** The
  code path is real (`opine_via_model()`, `governance/governance/agents/
  llm_backed.py:34-53`) and correctly validates through `parse_opinion()` —
  but **zero real recordings exist** (`governance/recordings/` is
  `.gitkeep`-only). Every call to `recommend(evaluation, mode="cached")`
  against an unrecorded evaluation raises `RecordingMissError` today.
- **Does live mode exist with a timeout and fallback?** No — `base.py:54-57`
  raises `NotImplementedError` unconditionally for `LIVE` on every path.
  Per-request timeouts and a `retryable` error flag exist as scaffolding for
  this, but no fallback logic executes anywhere. Correctly not yet due
  (3 Sept).
- **Any LLM calls in the stub path?** None. None of the four agent modules
  import anything from `governance.llm`; the coordinator's mode-dispatch
  (`coordinator.py`'s `_agent_node()`) only reaches `opine_via_model` (the
  only function that constructs an `LLMClient`) when `mode == CACHED`.

### Simulator-specific checks

- **Does `pytest simulator/` pass against `main`'s `shared/`?** Yes, 97/97.
- **Is the duplicate `wilson_lower_bound` gone?** Yes —
  `simulator/simulator/runner.py:47` imports it from `trust/`; zero local
  reimplementations anywhere in `simulator/`.
- **Is `agents/llm.py` removed?** Yes (`git ls-tree` confirms it's gone,
  deleted in `c4c09a2`) — **but the cleanup was incomplete**: `agents/
  cache.py`'s `DecisionCache` class is now orphaned dead code (its only
  purpose was caching `GeminiAgent` decisions; `git grep -n "DecisionCache"`
  shows it's defined and never imported anywhere else), its own docstring
  still says "File-based decision cache for the GeminiAgent" (`cache.py:4`),
  `agents/base.py:38`'s docstring still references `GeminiAgent`, and
  `simulator/pyproject.toml:10` still lists `google-generativeai>=0.8.0` as
  a dependency with nothing left to consume it.

### Frontend-specific checks

- **Has ANY of it been ported onto the frozen contracts?** No — the only
  commit touching `frontend/` since 23 Aug is `c4c09a2` (27 Aug), and that
  commit only deletes `nexttemp/` and adds a `typecheck` script; it does not
  touch a single page, component, or type file. Zero commits to `frontend/`
  in the 4 days since `backend/openapi.json` was published.
- **Does it still use the 3-tier model?** Yes —
  `frontend/src/types/api.ts:27`: `export type AutonomyTier = "low" |
  "medium" | "high"`, consumed in `AutonomyLadder.tsx`, `agents/page.tsx`,
  `agents/[id]/page.tsx`.
- **Are types still hand-written or generated?** Still 100% hand-written; no
  codegen script exists anywhere in the repo (`grep -n "openapi"` under
  `frontend/` → zero hits).

---

### Phase 2/3 (1–15 Sept) — achievability given what exists today

| Date | Who | Deliverable | Achievable as scoped? | What has to be true |
|---|---|---|---|---|
| **Tue 1 Sept** | All | Integration checkpoint — path unbroken | **No, not today.** The vertical slice is broken at its very first hop (§6) | `POST /api/v1/decisions` must actually persist and call the Policy Engine before this date, or the checkpoint is reported as missed the day before, per the standing rule |
| Wed 2 Sept | AD | Agent detail + approvals on real contracts | **Not achievable** — frontend hasn't started the 29 Aug deliverable yet | Sat 29 Aug's item must land first; frontend is currently 4 days idle against an unblocked dependency |
| Thu 3 Sept | VP | Approval workflow + RBAC | **Only if 31 Aug's wiring lands first** | `approve_recommendation()` needs a real `Session` + `apply_policy_version()` call, which needs the same DB-wiring work as decision ingest |
| Thu 3 Sept | VC | Live mode + timeout + fallback | **At risk, now larger than scoped** | Needs an `AzureOpenAIClient`, a primary/fallback mechanism that doesn't exist in any form today, and real Gemini recordings to fall back *to* |
| Fri 4 Sept | UK | Simulator finalized, deterministic seed | **Blocked on a wiring fix, not new work** | `simulator/simulator/api_client.py:85` targets a nonexistent `/invoices` route — this must be corrected to `/api/v1/decisions` before any real end-to-end run can be finalized |
| Sat 5 Sept | AD | Charts (Wilson band, 5-rung ladder step chart) | **Not achievable without the 29 Aug/2 Sept work first** | Frontend's type/endpoint corrections are a hard prerequisite |
| Sun 6 Sept | VP | Audit sampling end to end | **At risk** | Depends on the same DB-wiring chain as everything else in backend |
| Mon 7 Sept | AD | Real API, mocks retired | **At serious risk** | Requires the entire chain above to already be real |
| **Wed 9 Sept** | All | **FEATURE FREEZE** | **Not achievable without a scope cut** — see §10 | |

---

## 4. Quality of what landed

### Backend — Policy Engine fail-closed on 2 of 3 named paths; the third doesn't exist as an engine-level path

`backend/app/policy/engine.py`, quoted:

**(a) Missing policy version**, `engine.py:61-64`:
```python
if policy_version is None:
    return PolicyDecision(
        allowed=False, within_limit=False, reason_code=reason_codes.POLICY_VERSION_MISSING
    )
```
**(b) Internally inconsistent policy version**, `_is_valid()` (`engine.py:26-31`)
plus `engine.py:66-69` — both `allowed` and `within_limit` are `False`.
**(c) Unparseable invoice amount** — **no such path exists inside the Policy
Engine**. `Invoice.amount` (`app/policy/types.py:29`) is a plain `int` field
with no engine-level "invalid amount" reason code (`reason_codes.py` defines
exactly six codes, none for malformed input). Amount validity is enforced
one layer up, at the Pydantic boundary (`backend/app/schemas/decision.py:46`,
`amount: int = Field(gt=0)`) — which is currently unreachable from any real
ingest path (§3). **Finding: this specific fail-closed path is delegated
entirely to a layer that isn't wired to anything yet.**

Both Hypothesis property tests are real, not decorative:
`test_never_allows_an_amount_above_the_limit` and
`test_allowed_implies_within_limit` (`backend/tests/test_policy_properties.py`)
use `@given(amount=st.integers(min_value=-1_000_000, max_value=1_000_000),
policy=...)` — genuine randomized ranges including negatives, not fixed
cases. The import-boundary test (`test_policy_import_boundary.py`) does real
`ast.parse` + `ast.Import`/`ast.ImportFrom` walking against a
`FORBIDDEN_TOP_LEVEL_MODULES` frozenset, not string-grep — correctly avoids
substring false positives.

`app/models/guards.py:61-89`'s `before_flush` hook genuinely raises
(`ImmutableRowError`, `PolicyVersionRequiredError`), registered as a real
SQLAlchemy session-wide event, not a no-op or a warning.

### Backend — audit hash chain: canonical-JSON hashing is real; tamper *detection* is asserted only in docstrings, never tested

`app/models/audit_hash.py` matches the claim exactly:
`sha256(prev_hash + canonical_json(payload))`, sorted-key no-whitespace JSON.
`backend/tests/test_models_audit_hash.py` has 8 tests, all of which compute
hashes fresh from known inputs — **none mutates a persisted `AuditLogEntry`
row's `payload`/`hash` after construction and re-verifies against a
recomputed hash.** There is also no `verify_chain()`/`verify_audit()`
function anywhere in the repo (`grep -rn "def verify"` under `backend/` →
zero hits) — `app/models/audit_log.py:10-13` concedes this itself:
"Verifying the chain... is left as a read-side operation for whoever needs
it, not something this model does on every read." **The docstring's claim
("tamper-evident by construction") is architecturally sound but is not, as
of today, backed by any test that actually tampers with a row and catches
it, nor by any function that could catch it.**

### Trust ladder — real, unchanged, re-confirmed field-by-field this audit

`trust/trust_engine/ladder.py`, quoted:

**Two clawback triggers**, `ladder.py:74-86`, both `new_rung = max(current_rung
- 1, 0)` — the floor clamp — at lines 76 and 82 respectively.
**Six increase gates**, `ladder.py:92-123`: sample size (`INSUFFICIENT_SAMPLE`),
trust score (`TRUST_BELOW_THRESHOLD`), max rung (`AT_MAX_RUNG`), drift
(`DRIFT_ACTIVE`), cooldown (`COOLDOWN_ACTIVE`), clawback recovery
(`CLAWBACK_RECOVERY_PENDING`) — all present, all with distinct reason codes.
**Exactly one rung on increase**, `ladder.py:133`: `new_rung =
min(current_rung + 1, MAX_RUNG)`. `test_increase_never_skips_a_rung_
regardless_of_evidence_strength` (`test_ladder.py:70-72`) directly asserts a
trust score of 99.99 with 10,000 acted decisions still only moves one rung.
174 tests (173 passed, 1 environment-skip for `statsmodels` — see §7), ruff
clean, unchanged since the 27 Aug baseline. All four previously-dead
constants (`MIN_SAMPLE_FOR_INCREASE`, `MIN_TRUST_SCORE_FOR_INCREASE`,
`COOLDOWN_BETWEEN_INCREASES`, `CLEAN_DECISIONS_AFTER_CLAWBACK`) are now
genuinely read (`ladder.py:92,95,115,120`), not merely defined.

### Governance coordinator — real aggregation with an enforced ceiling assertion

`governance/governance/coordinator.py`, the dissent rule:
```python
if direction is Direction.INCREASE and has_dissent:
    direction = Direction.HOLD
    proposed_limit = evaluation.current_limit

if proposed_limit > max(evaluation.recommended_limit, evaluation.current_limit):
    raise AssertionError(
        f"governance proposed {proposed_limit}, above both the evidence-supported "
        f"{evaluation.recommended_limit} and the current {evaluation.current_limit}"
    )
```
An unconditional structural invariant, not gated behind a flag or test-only
path. `status=RecommendationStatus.PENDING` and `clamped=False,
clamped_from=None` are hardcoded with comments stating governance can never
self-approve or self-report clamping — "the backend owns clamping."
`governance/governance/agents/risk.py` and `compliance.py` were spot-checked
in full: both branch on real `TrustEvaluation` fields (an exposure
multiplier, `recent_criticals`, `rung_of()` invariant checks against
`reason_codes`), not fixed return values — backed by dedicated tests for
each distinct branch.

### No other stubbed-to-pass logic found

Spot-checked `trust/trust_engine/score.py`'s weight-renormalization (real
proportional redistribution over available components, `score.py:94-101`,
backed by `test_redistributed_weights_still_sum_to_one`), `simulator/
simulator/labeller.py`'s 10-rule cascade (real conditionals against
`shared.constants.AUTONOMY_LADDER`, e.g. `labeller.py:104-119`), and
`simulator/simulator/agents/scripted.py`'s rule-based decisions (real
tier-derived branching plus a probabilistic error-rate flip). Nothing found
short-circuited to make a suite pass, anywhere in this audit.

---

## 5. Boundary violations

| Lane | Result | Evidence |
|---|---|---|
| `trust/` | **Clean.** | `grep -rn -E "fastapi\|sqlalchemy\|psycopg\|redis\|celery\|requests\|httpx" trust/trust_engine/*.py trust/tests/*.py` → 6 hits, all the substring "redis" inside "redistribut(ed/ion)" — false positives. Zero real hits. Zero `datetime.now()`/`time.time()`/`open(`/bare `global` anywhere, including tests. |
| `governance/` | **Clean.** | `grep -rn -E "sqlalchemy\|psycopg\|fastapi\|from backend\|import backend"` under `governance/**/*.py` → zero hits. No `session.add`/`session.commit`/ORM import/policy mutation in `coordinator.py` or any agent file. |
| `backend/app/policy/` | **Clean.** | Manual grep of every import statement in all 5 files under `app/policy/` — no `sqlalchemy`, `psycopg`, `requests`, `httpx`, `socket`, `openai`, `anthropic`, `google`, `os`, or `time` anywhere. Confirmed independently of, and consistent with, the AST-based `test_policy_import_boundary.py`. |
| `simulator/` | **Clean of backend/DB imports.** | `grep -n "import backend\|from backend\|sqlalchemy\|psycopg"` under `simulator/` → zero hits. |
| `frontend/` | **One soft violation, not new.** | `frontend/src/components/charts/AccuracyGauge.tsx:18,23` and `HorizontalThresholdGauge.tsx:15,19`: `threshold = 0.85` hardcoded client-side, `isHealthy = wilsonLB >= threshold` — a pass/fail classification computed in TypeScript from a component default, not read from the API or any `shared/` constant (`trust/trust_engine/constants.py` has no `0.85` anywhere; the real gate is `MIN_TRUST_SCORE_FOR_INCREASE = 70.0` plus five other independent gates). Pre-existing from the 23 Aug divergence, not introduced since 27 Aug — but still live business logic in the frontend, worth fixing when the type/endpoint pass happens. |
| Cross-lane directory writes | **None found.** | Every commit's file list checked against its author since 27 Aug — no lane wrote into another lane's directory. |

---

## 6. The vertical slice — traced end to end, first break identified

Traced through the actual code, hop by hop, against `origin/main`:

1. **Simulator generates an invoice.** EXISTS, works in isolation
   (`simulator/simulator/generator.py`, 97 passing tests).
2. **Posts to the backend.** **BROKEN — wrong path.**
   `simulator/simulator/api_client.py:73-88`'s `submit_invoice()` POSTs to
   `f"{self.api_prefix}/invoices"`. The backend has **no `/invoices` path at
   all** — confirmed against `backend/openapi.json`'s full 18-path list. The
   backend's own docstring names the correct target:
   `backend/app/api/v1/simulation.py:31-33` says the simulator should post
   "each resulting decision to `POST /api/v1/decisions`." A live call today
   404s. This has never been caught because zero of the 97 simulator tests
   exercise `APIClient` — every `SimulationRunner` test constructs it with
   `api_client=None`.
3. **Policy Engine decides.** **BROKEN even at the correct endpoint.**
   `POST /api/v1/decisions` (`backend/app/api/v1/decisions.py:22-45`) never
   calls `evaluate_decision` — it's a hand-fabricating stub (§3).
4. **Persisted with an audit entry.** **BROKEN.** `append_entry` has exactly
   one production caller anywhere in the repo, `backend/app/seed.py:867`.
5. **Trust engine evaluates.** **BROKEN — completely disconnected.**
   `grep -rn "trust_engine" backend/app/` → zero real imports (only
   documentation-comment mentions of constant names). `GET /agents/{id}/trust`
   is a fixture stub whose own docstring says "Once implemented: calls
   `trust_engine.evaluate(...)`." Even `backend/app/seed.py` hand-authors
   trust-evaluation rows rather than computing them via the real engine.
6. **Governance recommends.** **BROKEN — completely disconnected.**
   `grep -rn "from governance\|import governance" .` outside `governance/`
   itself → zero hits anywhere in the repo. `coordinator.recommend()` is
   called only from `governance/tests/`.
7. **Hard ceiling clamps.** **BROKEN, and it's the one Policy Engine function
   with zero production callers of any kind — not even `seed.py` calls it.**
   `clamp_recommendation`'s only callers are `backend/tests/
   test_policy_ceiling.py` and `test_policy_properties.py`.
8. **Human approves → new policy version.** **BROKEN, and the code documents
   its own bypass.** `approve_recommendation()`
   (`backend/app/api/v1/recommendations.py:73-92`) calls `_decide()`, which
   does `.model_copy()` on an in-memory fixture — no `Session`, no
   `apply_policy_version` call. That function has callers only in
   `backend/app/seed.py` (8 sites) and one test file.
9. **Dashboard shows it.** **BROKEN, with path drift layered on top of the
   missing wiring.** `frontend/src/lib/api-client.ts` targets paths that
   mostly don't exist independent of the backend-DB gap: `/invoices` (same
   wrong path as the simulator), `/approvals` (backend has no such router —
   only `/recommendations/{id}/approve|reject`), `/audit` (real path is
   `/audit-log`), `/agents/{id}/decisions` and `/agents/{id}/autonomy-history`
   (neither exists). Only `agentsApi.list/get` and
   `simulationApi.start/getRun` line up with real backend paths. MSW is
   **disabled by default** (`NEXT_PUBLIC_MSW_ENABLED` unset,
   `frontend/src/components/ui/Providers.tsx:37-44`), so a running dev app
   fires real, mismatched `fetch()` calls by default — and even the MSW
   mock handlers (`frontend/src/mocks/handlers.ts`) mirror the same stale
   invented paths as `api-client.ts`, not the real committed
   `backend/openapi.json`.

**First break: hop 2, the simulator→backend POST.** The chain never
reconnects after that — every subsequent hop is independently unwired.

**Authoritative confirmation from the team's own record** —
`docs/DECISION_LOG.md`'s 2026-08-31 PR #17 entry: *"does not wire any API
endpoint to the database — the stubs in `backend/app/api/v1/` are untouched;
that is Mon 31 Aug / Thu 3 Sept work."* Every finding above matches this
exactly; the gap was scheduled, not accidental — but the schedule's own date
(31 Aug) is today, and the work hasn't landed as of this audit.

**What it takes to close it, in order:**
1. Fix `simulator/simulator/api_client.py:85` to target `/api/v1/decisions`
   with `DecisionCreate`'s flat body shape, not the nested `{"invoice":
   ..., "agent_id": ...}` shape.
2. Rewrite `create_decision()` to open a `Session`, call `evaluate_decision`,
   persist a real `Decision` row, call `append_entry` — all in one
   transaction, exactly as its own docstring already specifies.
3. Wire `GET /agents/{id}/trust` (and a trigger point) to call
   `trust_engine.evaluate()` with the agent's real persisted decision
   history.
4. Wire a recommendation-generation path to call
   `governance.coordinator.recommend()` with real trust evidence.
5. Call `clamp_recommendation` on governance's proposed limit before
   persisting a `Recommendation`.
6. Rewrite `approve_recommendation()` to write an `Approval` row and call
   `apply_policy_version()` in the same transaction.
7. Fix `frontend/src/lib/api-client.ts`'s path mismatches and regenerate
   `frontend/src/mocks/handlers.ts` from the real `backend/openapi.json`.

Nothing above requires new architecture — every module named already exists
and is independently well-tested. The only missing artifact is the glue
code inside `backend/app/api/v1/*.py`.

---

## 7. Tests, CI, and the environment

### Per-lane results (exact, from junit-XML-parsed runs)

| Lane | Pass | Fail | Skip | Total | Notes |
|---|---:|---:|---:|---:|---|
| `trust/` | 173 | 0 | 1 | 174 | Skip: `test_wilson.py:109`, statsmodels not installed |
| `simulator/` | 97 | 0 | 0 | 97 | 20 `DeprecationWarning`s, `runner.py:112`'s `datetime.utcnow()` |
| `governance/` | 193 | 0 | 0 | 193 | |
| `backend/` | 127 | 0 | 0 | 127 | |
| `frontend/` | — | — | — | 0 | No test runner configured |
| **Grand total** | **590** | **0** | **1** | **591** | |

**The "338" figure cited externally is wrong and stale, by 253 tests.**
`interactivehtml/index.html` cites it twice — line 244 (`<div
class="v">338</div>`) and line 399 ("pytest · Hypothesis — 338 tests
including property-based statistics tests") — both dated to a "Status · 27
August 2026" snapshot, last touched by commit `5fc4691` (29 Aug), before
PRs #12/#15/#16/#17/#18 all landed. `docs/CONTEXT.md` does not itself cite
"338" (grepped, no match). `docs/ONBOARDING.md:51-54`'s expected per-lane
counts are separately stale in the other direction — 112/97/67/56 vs.
today's real 173/97/193/127.

### Is `main` green?

**Yes.** `gh run list --branch main --limit 5` — latest run (`0ad103a`, PR
#19) is `success`; every merge event from 27 Aug onward (`88871e8`, `4f0af61`,
through `0ad103a`) shows `success`. Failed runs exist only on feature
branches pre-merge (`uk/autonomy-ladder`'s lint failure, `ad/simulator-
frontend`'s pre-fix `typecheck` failure) — the normal case, not a red merge.

**Caveat: "green" is silent on an entire lane.** `.github/workflows/ci.yml`
never runs `pytest simulator/tests` at all — no step for it exists, confirmed
against both the yaml (`grep -c simulator .github/workflows/ci.yml` → 0) and
the actual latest run's step list. The 97 simulator tests, and simulator's
78 ruff errors, have never once been checked by CI since the port landed on
27 Aug.

### Did anything merge with failing CI?

**No.** Every merge-commit push event on `main` from 27 Aug onward is green.

### Code added since 27 Aug with no test at all

- `backend/app/models/users.py`'s `User` model — zero test coverage, zero
  runtime usage; its own docstring admits this ("deliberately out of scope
  for this branch"). `test_seed.py`'s `test_every_table_has_at_least_one_row`
  deliberately excludes `User` from its checked list.
- `backend/app/models/audit_log.py` has no dedicated unit test file
  (`test_models_audit_log.py` doesn't exist); exercised only indirectly
  through `test_seed.py`'s integration-style checks, not in isolation.
- `backend/app/models/{approvals,decisions,invoices,recommendations,
  trust_evaluations,types,base}.py` — no per-model unit test files exist for
  any of these, unlike `agents`/`audit_hash`/`guards`, which have dedicated
  suites.
- `simulator/`'s incomplete `llm.py` cleanup (`agents/cache.py`'s orphaned
  `DecisionCache`) is itself evidence of dead, never-exercised code — flagged
  by `ruff`'s `RUF059`/`F841` findings.

### `ruff check` per lane

```
trust/       — All checks passed!
governance/  — All checks passed!
backend/     — All checks passed!
simulator/   — 78 errors (46 auto-fixable): 21 I001, 13 F401, 8 UP045,
                7 DTZ011, 6 BLE001, 5 B008, 5 RUF059, and 8 smaller findings
```
`simulator/` remains entirely absent from `.github/workflows/ci.yml`'s
`ruff check trust/ backend/ governance/` line — unchanged since 27 Aug.

### Environment — Windows

**`make` genuinely does not exist** on this Windows machine (confirmed both
in native PowerShell and git-bash) — this is exactly RISKS.md R13, still
`OPEN`. `docs/ONBOARDING.md`'s primary instruction, `make setup`, cannot run
as written.

**PowerShell coverage is incomplete.** `scripts/` contains exactly 3 files:
`help.ps1`, `setup.ps1`, `up.ps1`. Of the Makefile's 9 named targets (`setup`,
`up`, `down`, `db-reset`, `test`, `openapi`, `lint`, `fmt`, `dev` — plus an
unlisted 10th, `frontend`), only **2 have a Windows equivalent**. **7 targets
have no PowerShell script at all: `down`, `db-reset`, `test`, `openapi`,
`lint`, `fmt`, `dev`** (`frontend` too). `README.md:14-16` oversells this
("See `make help`... for every other target" implies parity that doesn't
exist). The 3 existing scripts parse and run cleanly (one cosmetic bug: `help
.ps1` mangles an em-dash under default console encoding). Docker itself works
fine on this machine (`docker compose config` validates clean; `aagp-db` is
already up and healthy) — the gap is the missing scripts, not Docker or the
compose file.

**Every documented command that fails as written**: exactly one —
`make setup` / `make ...` in general, with the literal error `'make' is not
recognized as an internal or external command` (native PowerShell) /
`bash: make: command not found` (git-bash). Everything else documented
(the 3 `.ps1` scripts, `pytest <lane> -q`, `ruff check`, `docker compose
config`) runs correctly as written — the Windows gap is *absence* of
scripts for 7 targets, not breakage of what exists.

---

## 8. Docs drift

| Claim | Where | Reality | Gap |
|---|---|---|---|
| "338" tests | `interactivehtml/index.html:244,399` | 591 tests exist today (590 pass, 1 skip) | Off by 253, last touched 29 Aug |
| "GOVERNANCE · 67 TESTS" | `interactivehtml/index.html:1296` | 193 governance tests | Off by 126 |
| `docs/ONBOARDING.md:51-54` expected counts (112/97/67/56) | `docs/ONBOARDING.md` | Real: 173/97/193/127 | Understates trust and governance significantly; a new contributor following this literally would think something regressed |
| `docs/CONTEXT.md:207` — "On `vc/gemini-client` (**PR #15 open**)... `vc/swappable-providers` (**PR #16, stacked on #15**)" | `docs/CONTEXT.md` | Both merged directly to `main` (#15: 29 Aug, #16: 30 Aug) | Branch-topology framing stale; the row's *code-content* description (193 tests, cached mode plumbing, recordings empty) remains accurate and should not be revised |
| ADR-0012 `Status: Proposed... Needs a decision from the team` | `docs/adr/0012-...md:5` | Team has since decided (Azure OpenAI primary, Gemini fallback), per user confirmation this audit | Decision made outside the repo, never recorded in the ADR or `docs/DECISION_LOG.md`; zero mention of "Azure" anywhere in the repository |
| `docs/DEADLINES.md`'s AD row, Sat 29 Aug | `docs/DEADLINES.md:59` | Missed 2 days ago as of this audit, and no `docs/RISKS.md` entry or `DECISION_LOG.md` note records the miss | Violates the standing rule "a missed deadline is reported the day before it slips, not after" — the same pattern the 27 Aug audit already flagged for backend's two misses has recurred for frontend |
| `docs/RISKS.md` R13 status: `OPEN` | `docs/RISKS.md:24` | Still accurate — `make` confirmed absent, PowerShell scripts still only cover 2 of 9 targets | Not stale, correctly still open; worth noting the mitigation text ("Windows scripts... still need verifying") undersells the gap now that the exact missing-target count is known |
| `docs/lanes/uk.md:301` "last four are currently dead" (constants) | `docs/lanes/uk.md` | All four now genuinely read in `ladder.py` | Stale — this lane doc predates the ladder work and was never updated after 26 Aug; low urgency since `docs/DEADLINES.md`/`docs/RISKS.md` already reflect the ladder's completion elsewhere |

Not stale, checked and confirmed accurate: `docs/RISKS.md` R1–R12's current
statuses (spot-checked against this audit's own findings, no contradictions
found); ADR-0013 and ADR-0014 (both `Accepted`, both match the code exactly,
confirmed this audit); `docs/DECISION_LOG.md`'s entries for PRs #17/#18/#19
(all accurately describe what shipped, including the honest "does not wire
any API endpoint" admission that this audit independently confirmed).

### Addendum — tooling claims, confirmed IN or OUT

| Tool | Claimed for | Status | Evidence |
|---|---|---|---|
| **statsmodels** | Wilson-interval cross-validation | **IN, but never executes** | Declared `trust/pyproject.toml:13` (dev group); real test at `trust/tests/test_wilson.py:107-109` using `pytest.importorskip`. Not installed in this env or in CI (`Makefile:33-35` deliberately omits it, RISKS.md R7) — the cross-validation has never actually run anywhere this project's CI or local setup touches. Citing it externally as "cross-validated against statsmodels" without qualifying that the check currently always skips is an overclaim. |
| **Hypothesis property tests** | "338 tests including property-based statistics tests" | **IN** | `trust/tests/test_wilson_properties.py` (8 real `@given` tests), `backend/tests/test_policy_properties.py` (5 real `@given` tests). Declared dependencies, genuinely used. |
| **Recharts** | Frontend charting | **IN** | `frontend/package.json:18` (`recharts ^3.10.1`), imported at `AutonomyTimeline.tsx:20`. |
| **shadcn/ui** | Fixed frontend stack | **OUT** | Zero hits in `package.json`; no `components.json`; `components/ui/` contains 3 hand-rolled files, none shadcn-generated. |
| **tenacity** | Retry logic in LLM clients | **OUT** | Zero hits anywhere. What exists instead: a `retryable: bool` flag per error class (`governance/governance/llm/errors.py:21-95`) and per-request timeouts — scaffolding for the not-yet-built live-mode retry logic, not an active retry mechanism. |
| **respx** | Mocking `httpx` in governance tests | **OUT** | Zero hits. Uses `httpx.MockTransport` directly via a local helper (`governance/tests/test_llm.py:59-60`), injected through each client's `generate(..., client=...)` parameter. |
| **pytest-httpx** | Alternative httpx mocking | **OUT** | Zero hits. Same `MockTransport` mechanism covers this; env/key mocking uses pytest's built-in `monkeypatch`. |

**Direct summary: 3 of 7 genuinely IN (Hypothesis, Recharts, statsmodels-as-
declared-with-real-but-always-skipped test code); shadcn/ui, tenacity,
respx, and pytest-httpx are all fully OUT.**

---

## 9. Per-person briefs

### Varun P. (backend, lead)

**Shipped since 27 Aug:** PR #11 (openapi.json + 18 stub endpoints, first
real backend code), PR #17 (SQLAlchemy models, Alembic migration, seed
script, Policy Engine as a pure module — fail-closed on every named path,
AST import-boundary tested, real Hypothesis property tests), PR #18 (fixed
a `recommendations.generated_at` schema gap flagged in review), PR #19
(branch cleanup + decision log). Also authored `c4c09a2`, which did
simulator/frontend CI-unblocking work (`typecheck` script, `nexttemp/`
removal, `agents/llm.py` deletion) that wasn't formally either lane owner's
commit.

**Next deliverable:** Mon 31 Aug (today) — decision ingest, real persistence,
hash-chained audit log. **MISSING** — models and the append helper exist,
nothing is wired to a live request path.

**What's missing, commit-sized, ordered so nothing downstream stays blocked:**
1. Rewrite `create_decision()` (`backend/app/api/v1/decisions.py:22-45`) to
   open a `Session`, call `evaluate_decision`, persist a real `Decision` row,
   and call `append_entry` in one transaction — this alone closes today's
   deadline and unblocks the entire vertical slice, which breaks at exactly
   this point (§6).
2. Confirm `/api/v1/decisions` (flat body) is the canonical ingest path and
   tell Utkarsh directly — the simulator's `api_client.py:85` currently posts
   to a nonexistent `/invoices` route with a nested body shape; this is a
   one-line fix on his side once he knows which endpoint is real.
3. Wire `GET /agents/{id}/trust` to call `trust_engine.evaluate()` with the
   agent's persisted decision history instead of `TRUST_CURRENT` fixtures.
4. Wire a recommendation-generation path to call
   `governance.coordinator.recommend()`, then `clamp_recommendation` on the
   result before persisting — `clamp_recommendation` currently has zero
   production callers anywhere, including `seed.py`.
5. Rewrite `approve_recommendation()`/`reject_recommendation()` to write an
   `Approval` row and call `apply_policy_version()` in the same transaction.
6. Add a dedicated `test_models_audit_log.py` with a real tamper-mutation
   test (mutate a persisted row's payload, recompute, assert mismatch) — the
   current 8 audit-hash tests never actually tamper with a stored row.
7. Fix the stale docs this audit found: `docs/ONBOARDING.md:51-54`'s expected
   test counts (112/97/67/56 → 173/97/193/127), `interactivehtml/
   index.html`'s "338"/"67 TESTS" (→ 591/193), `docs/CONTEXT.md:207`'s
   "PR #15 open"/"PR #16 stacked on #15" (both merged).
8. Close the Windows script gap (RISKS.md R13) — 7 of 9 Makefile targets
   (`down`, `db-reset`, `test`, `openapi`, `lint`, `fmt`, `dev`) have no
   PowerShell equivalent in `scripts/`; a Windows contributor following
   `docs/ONBOARDING.md` today can bring the DB up but has no scripted way to
   migrate/seed it.

**Delete as dead weight:** nothing in your own lane; flag to Utkarsh that
`simulator/simulator/agents/cache.py`'s `DecisionCache` is orphaned dead
code and `google-generativeai` is an unused dependency, both leftover from
the incomplete `llm.py` removal.

**Blocked by:** nobody structurally — `openapi.json` has existed since 27
Aug. **Blocking:** everyone — items 1-5 above are the entire vertical slice;
nothing downstream (Tue 1 Sept checkpoint, Wed 2 Sept frontend work, Thu 3
Sept approval workflow) can land until this ships.

---

### Utkarsh (trust, then simulator)

**Shipped since 27 Aug:** One style-only commit (`091bdf6`, import-order
fix, no logic change, 174 tests unchanged) — the trust lane itself is
complete, correct, and stable; nothing found in this audit regressed or
needs rework. **On simulator, which you've owned since 27 Aug: zero commits**
— the one simulator-touching commit in this window (`c4c09a2`) was authored
by Varun P., not you.

**Next deliverable:** Fri 4 Sept — simulator finalized (phases, degradation
injection, deterministic seed reproducing the ten-beat arc).

**What's missing, commit-sized, ordered so the blocker comes first:**
1. Fix `simulator/simulator/api_client.py:85` — it POSTs to `/api/v1/invoices`
   with a nested `{"invoice": {...}, "agent_id": ...}` body; the real backend
   route is `POST /api/v1/decisions` with a flat `DecisionCreate` body
   (`invoice_id, amount, action, ground_truth, agent_id, reason`). This is
   the literal first break in the vertical slice (§6) and blocks the Tue 1
   Sept checkpoint entirely.
2. Finish the `agents/llm.py` cleanup PR #8 left incomplete: delete
   `agents/cache.py` (orphaned `DecisionCache`, unused since `GeminiAgent`'s
   removal), drop `google-generativeai` from `simulator/pyproject.toml`, fix
   the stale `GeminiAgent`-referencing docstrings in `agents/base.py:38` and
   `fixtures/cache/.gitkeep`.
3. Get `simulator/` added to `.github/workflows/ci.yml`'s `ruff check` and
   `pytest` steps — it's currently invisible to CI entirely (78 lint errors,
   97 tests, never once checked on any run since the port landed). Coordinate
   with Varun P. since this is a shared CI file.
4. Finalize phase tuning (good/degraded/recovery) against the 5-rung ladder
   for the ten-beat demo arc, and commit fixtures so the demo can replay
   without live generation — the 27 Aug audit flagged fixture regeneration
   as unverified; confirm this explicitly.
5. Replace `runner.py:112`'s `datetime.utcnow()` (20 deprecation warnings) —
   low priority, but free to fix while touching this file.

**Delete as dead weight:** `agents/cache.py`, the `google-generativeai`
dependency.

**Blocked by:** nobody for items 1-2, 4-5 (your own lane). Item 3 needs
coordination with whoever maintains CI.

---

### Varun C. (governance)

**Shipped since 27 Aug:** The most complete work of the week. PR #12
(prompt scaffolding, Gemini-dialect schema), PR #15 (Gemini HTTP client,
recording store, working cached-mode plumbing, 407 new tests), PR #16
(Claude/OpenAI clients, `LLMClient` protocol, `GOVERNANCE_PROVIDER` registry,
ADR-0012, the cache-key model-collision fix, 389 more new tests). 193 tests,
ruff clean, git author identity corrected as of `c7b82d4` (29 Aug).

**Next deliverable:** Sun 30 Aug — cached mode with real recorded responses
(now overdue by 1 day). **PARTIAL** — code is done; `governance/recordings/`
has zero real recordings. Also Thu 3 Sept — live mode + timeout + fallback,
now larger in scope than originally planned given the Azure decision.

**What's missing, commit-sized, ordered so the overdue item comes first:**
1. Run `python -m governance.record` against a real API key for the five
   representative scenarios already built (`governance/governance/
   scenarios.py`) and commit the resulting recordings. This is the single
   concrete undelivered artifact from 30 Aug — everything else about that
   deliverable is genuinely done.
2. Update ADR-0012's `Status` line off "Proposed" and add the Azure OpenAI
   decision to it (or a new ADR) — right now there is **zero mention of
   Azure anywhere in the repository**, despite it being the confirmed
   direction.
3. Build an `AzureOpenAIClient` implementing `LLMClient`
   (`governance/governance/llm/base.py`'s 4-member protocol) — using the
   SDK's `AzureOpenAI` client (not the plain `OpenAI` client
   `openai_client.py` currently wraps), with `azure_endpoint`/`api_version`/
   deployment-name config. Register it in `registry.py`'s `_BUILDERS`.
4. Design and implement the primary-with-fallback mechanism itself —
   `registry.py`'s `resolve_provider()` currently selects exactly one
   provider with no fallback concept at all. This is genuinely the substance
   of the Thu 3 Sept live-mode deliverable, not separate work; scope it as
   such.
5. Given how much new scope items 3-4 represent this close to freeze, raise
   explicitly with the team whether live Azure/Gemini mode should move onto
   the cut list for the demo (cached mode with real Gemini recordings only)
   — see §10.
6. Update `docs/CONTEXT.md:207`'s governance row — still says "PR #15 open"
   and "PR #16... stacked on #15," both merged since.

**Delete as dead weight:** nothing found — cleanest lane in the audit.

**Blocked by:** nobody. **Blocking:** the backend's recommendation-generation
wiring (Varun P.'s checklist item 4) needs `recommend()` to be meaningfully
callable in whatever mode the demo runs — which needs item 1 (real
recordings) done first for cached mode to produce anything but a
`RecordingMissError`.

---

### Adhya (simulator port — delivered; frontend — now the most overdue lane)

**Shipped since 27 Aug:** Nothing. Your simulator port work (PR #8) landed
right at the 27 Aug boundary and was already credited in the baseline audit.
Since then, `frontend/` has had zero commits from you — the one commit that
touched it (`c4c09a2`, dropping `nexttemp/` and adding a `typecheck` script)
was authored by Varun P., not you.

**Next deliverable:** Sat 29 Aug — frontend types from `openapi.json`, hand-
written types deleted, `nexttemp/` removed, `typecheck` added, `shadcn/ui`
added. **PARTIAL, now 2 days late** — 2 of 4 sub-items done (by someone
else), types still 100% hand-written, `shadcn/ui` still absent, no codegen
pipeline exists.

**What's missing, commit-sized, ordered so the blocker comes first:**
1. **Nothing is actually blocking you** — `backend/openapi.json` has existed
   since 27 Aug evening. Add a codegen script (e.g. `openapi-typescript`) to
   `frontend/package.json`, regenerate `frontend/src/types/api.ts` from it,
   and delete the hand-written version (`types/api.ts:1-6` still says
   "mirroring shared/contracts.py Pydantic models" by hand). This has been
   actionable for 4 days.
2. Fix `frontend/src/lib/api-client.ts`'s endpoint paths against the real
   backend: `/invoices` → `/decisions`, `/approvals` → `/recommendations/
   {id}/approve|reject`, `/audit` → `/audit-log`, `/agents/{id}/decisions`
   and `/agents/{id}/autonomy-history` → the real `/agents/{id}/trust` and
   `/agents/{id}/policy-versions` endpoints, drop or fix
   `simulationApi.listRuns` (no bare `GET /simulation/runs` exists).
3. Regenerate `frontend/src/mocks/handlers.ts` to match — it currently
   mirrors the same stale invented paths as `api-client.ts`, not the real
   committed contract, so even the mock layer is wrong.
4. Replace the hardcoded 3-tier model still baked into
   `AutonomyLadder.tsx`, `agents/page.tsx`, `agents/[id]/page.tsx` with the
   real 5-rung ladder.
5. Add `shadcn/ui` — never installed despite being a fixed-stack requirement
   since before 23 Aug.
6. Remove the invented `0.85` hardcoded threshold in `AccuracyGauge.tsx`/
   `HorizontalThresholdGauge.tsx` (§5) — it's not sourced from the API or any
   `shared/` constant; replace with the real API-supplied eligibility signal.

**Delete as dead weight:** the hand-written `types/api.ts`, once codegen
lands (item 1).

**Blocked by:** nobody — this has been an unblocked, actionable deliverable
for 4 days. Flag this gap directly rather than letting it read as "waiting
on backend," since it isn't anymore.

---

## 10. Critical path to 15 September

Fifteen days remain, nine before feature freeze.

**Three things most endangering the deadline, in order:**

1. **The vertical slice is disconnected end to end, and every individual
   piece being real and well-tested has been masking this.** 591 tests pass
   and every lane's own logic is genuinely correct — but zero of the 9 demo
   hops actually hand data to the next one via real code. The Tue 1 Sept
   integration checkpoint's own check is "the path must be unbroken," and
   today it breaks at hop 1 (§6). This is a materially worse position than a
   missing module: it looks finished lane-by-lane, so the gap is easy to
   miss until someone actually tries to run the demo.
2. **Frontend has been completely idle for 4 days against an unblocked
   deliverable.** `backend/openapi.json` has existed since 27 Aug evening;
   Adhya's 29 Aug deliverable (types from it, `shadcn/ui`, dead types
   deleted) is now 2 days late with zero movement, and no `docs/RISKS.md`
   entry or `DECISION_LOG.md` note records the miss — the same silent-miss
   pattern the 27 Aug audit already flagged for backend has now recurred for
   frontend.
3. **The Azure OpenAI pivot adds real, unbudgeted scope to an already-tight
   governance schedule.** The registry supports one provider per agent, not
   primary/fallback; Azure needs a structurally different client than the
   vanilla OpenAI one already built; and this decision hasn't been written
   into ADR-0012 or `docs/DECISION_LOG.md` yet, so it isn't visible to
   anyone reading the docs as the team's actual plan.

**Is the 9 Sept feature freeze achievable without cutting anything? No.**
The 9-day runway to freeze has to absorb: the entire 6-step backend↔trust↔
governance↔frontend wiring chain (§6), frontend's 29 Aug catch-up plus its
own scheduled 2/5/7 Sept work, governance's undelivered Gemini recordings
plus a new Azure client plus a fallback mechanism that doesn't exist in any
form, and the Tue 1 Sept checkpoint itself — which cannot pass as scoped
today. The team's own buffer (`docs/DEADLINES.md`: "two genuinely empty
days... 14 Sept, and the slack inside Phase 2") is not enough to absorb a
slipped 1 Sept checkpoint *and* the Azure work in the same window.

**What must be cut, and by when:** by **Tue 1 Sept** (the checkpoint date
itself — do not let this decision drift past it). Recommend widening cut #1
on the existing list explicitly: **"live mode of any provider (Gemini or
Azure) — cached mode is the demo default regardless of which provider ends
up wired."** This one decision resolves the Azure fallback-mechanism problem
(don't build it for the demo) and keeps governance's remaining Sept work to
"get real Gemini recordings committed," which is achievable this week.

**Cut-list re-check** (`docs/DEADLINES.md` bottom): still fundamentally the
right list and order — nothing found in this audit changes it. One update:
item 1 ("Live Gemini mode") should be reworded to cover *any* provider now
that Azure is in play, per above. If anything, frontend's 4-day idle stretch
makes item 5 ("if the frontend port runs long, rebuild clean") more live
today than it was on 27 Aug, not less — worth a decision alongside the 1
Sept checkpoint, not after.

**Assuming zero further slippage from here, what the 15 Sept demo actually
looks like**: cached-mode governance recommendations, built on real
committed Gemini recordings, driving a fully wired backend — decision
ingest → Policy Engine → persistence → audit chain → trust evaluation →
governance recommendation → hard ceiling clamp → human approval → new
policy version — shown on a frontend now pointed at real generated types
and corrected endpoint paths, running the ten-beat arc from one simulator
command. **What will visibly be missing**: live LLM calls of any kind
(Gemini or Azure), the dedicated audit-sampling review screen (kept as
backend-only), RBAC beyond a single role check, the simulation console
(CLI-driven instead), and — unless the Azure decision gets coded and tested
before freeze — Azure OpenAI as an active provider at all, with Gemini
remaining the sole provider actually exercised in the demo build.
