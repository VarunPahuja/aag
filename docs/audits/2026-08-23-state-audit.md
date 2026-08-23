# State Audit — 2026-08-23

Read-only. Nothing in this repository was written, edited, staged, committed,
pushed, merged, rebased, deleted, or formatted to produce this report except
this file itself. Verification work (running tests, `npm ci`, `uv sync`,
`npm run build`, `tsc`) was done in a disposable `git worktree` under the
system temp directory, which has since been removed; it never touched the
tracked repository.

Baseline: `docs/audits/2026-08-21-pre-merge-audit.md` (exists only on the
unmerged branch `origin/docs/audit-and-risk-fix` — see §1/§8). All SHAs below
as of this audit:

| Ref | SHA |
|---|---|
| `origin/main` | `7922bc0` |
| `origin/ad/simulator-frontend` | `1b1c416` |
| `origin/docs/audit-and-risk-fix` | `9e5b564` |
| `origin/uk/trust` | `70b3b96` (merged) |
| `origin/uk/shared-trust-contracts` | `444fdc0` (merged) |
| `origin/shared/v1-1-recommendation-and-audit-sample` | `ad4b58c` (merged) |
| `origin/chore/infra-baseline` | `051e202` (merged) |
| `origin/chore/rename-and-docs` | `03358a1` (merged) |
| `origin/vc/governance` | `c126543` (= initial scaffold) |
| `origin/vp/backend` | `c126543` (= initial scaffold) |

**Housekeeping note, not covered by any task below but relevant to everything
in it:** `docs/DEADLINES.md` and `docs/lanes/*.md` — the files this audit was
instructed to read as ground truth for deadlines and lane ownership — are
**untracked** in this working tree (`git status`: `?? docs/DEADLINES.md`, `??
docs/lanes/`). They exist nowhere in git history, on any branch. Every
deadline and ownership claim in this report is sourced from files that are
not themselves under version control yet.

---

## 1. Branch map

### Local vs. remote ref divergence (flagged first, per instructions)

| Local branch | Local SHA | Remote SHA | Divergent? |
|---|---|---|---|
| `ad/simulator-frontend` | `c126543` | `1b1c416` | **YES** — local is 1 commit *behind*, missing Adhya's entire 2026-08-23 push |
| `uk/trust` | `c126543` | `70b3b96` | **YES** — local is 3 commits behind (same staleness the 21 Aug audit flagged as R8 in RISKS.md; still not fetched two days later) |
| `vc/governance` | `c126543` | `c126543` | synced (both empty) |
| `vp/backend` | `c126543` | `c126543` | synced (both empty) |
| `chore/infra-baseline` | `051e202` | `051e202` | synced |
| `docs/audit-and-risk-fix` | `9e5b564` | `9e5b564` | synced |
| `shared/v1-1-recommendation-and-audit-sample` | `ad4b58c` | `ad4b58c` | synced |
| `main` | `1a52413` | `7922bc0` | **YES** — local `main` is 1 commit behind origin (missing the infra-baseline merge) |

Two remote branches have no local counterpart at all: `origin/uk/shared-trust-contracts` and `origin/chore/rename-and-docs` (both already merged into main, so this is harmless, but worth knowing before anyone tries to `git branch -a` their way to "what's out there").

### Full branch table

| Branch | Last commit | Author | Date | Ahead of `origin/main` | Behind | Merge-base | Merges cleanly now? | Stale? | Duplicates work on main? |
|---|---|---|---|---:|---:|---|---|---|---|
| `origin/main` | `7922bc0` | Varun Pahuja | 2026-08-21 21:52 | — | — | — | — | — | — |
| `origin/uk/trust` | `70b3b96` | UtkarshSahgal | 2026-08-20 15:57 | 0 | 11 | `70b3b96` (= tip) | N/A — ancestor of main | N/A | No — merged |
| `origin/uk/shared-trust-contracts` | `444fdc0` | UtkarshSahgal | 2026-08-19 17:02 | 0 | 13 | `444fdc0` (= tip) | N/A — ancestor of main | N/A | No — merged |
| `origin/chore/rename-and-docs` | `03358a1` | Varun | 2026-08-21 18:37 | 0 | 7 | `03358a1` (= tip) | N/A — ancestor of main | N/A | No — merged |
| `origin/shared/v1-1-recommendation-and-audit-sample` | `ad4b58c` | Varun | 2026-08-21 19:51 | 0 | 5 | `ad4b58c` (= tip) | N/A — ancestor of main | N/A | No — merged |
| `origin/chore/infra-baseline` | `051e202` | Varun | 2026-08-21 21:49 | 0 | 1 | `051e202` (= tip) | N/A — ancestor of main | N/A | No — merged |
| `origin/vc/governance` | `c126543` | Varun | 2026-08-17 23:56 | 0 | 14 | `c126543` | Trivially — it's an ancestor of main, there's nothing to merge | N/A | **No work exists to duplicate — zero commits since the initial scaffold, 6 days later** |
| `origin/vp/backend` | `c126543` | Varun | 2026-08-17 23:56 | 0 | 14 | `c126543` | Trivially — same as above | N/A | **Same — zero commits since scaffold** |
| `origin/docs/audit-and-risk-fix` | `9e5b564` | Varun | 2026-08-21 18:49 | 1 | 6 | `ee4e141` | **Yes, cleanly** (verified with `git merge-tree`, zero conflicts) | No — nothing on main since its base touches `docs/RISKS.md` or `docs/audits/` | No |
| `origin/ad/simulator-frontend` | `1b1c416` | Adhya Sharma | 2026-08-23 15:37 | 1 | 14 | `c126543` (the 17 Aug scaffold — 6 days and 14 commits stale) | **No — 5 files conflict** (see §2) | **Yes, severely** — base predates `shared/` existing at all | **Yes — see §2, this is the headline finding** |

### Commits on unmerged branches

**`origin/docs/audit-and-risk-fix`** (1 commit ahead of main):

| SHA | Author | Date | Subject | Files touched |
|---|---|---|---|---|
| `9e5b564` | Varun | 2026-08-21 18:49:12 | docs: correct RISKS.md timeline to three weeks, track pre-merge audit | `docs/RISKS.md` (1 line), `docs/audits/2026-08-21-pre-merge-audit.md` (new, 330 lines) |

**`origin/ad/simulator-frontend`** (1 commit ahead of main):

| SHA | Author | Date | Subject | Files touched |
|---|---|---|---|---|
| `1b1c416` | Adhya Sharma | 2026-08-23 15:37:02 | feat(simulator): implement frontend interface and update simulator workflow | 82 files, +35,585 lines. Full list in §3. |

### CI status by branch (via `gh run list`)

| Branch | Latest CI run | Result |
|---|---|---|
| `main` (PR #3 merge) | 2026-08-21 16:22 | **success** |
| `chore/infra-baseline` (as PR) | 2026-08-21 16:20 | success |
| `main` (PR #2 merge) | 2026-08-21 14:25 | **failure** — merged anyway (see below) |
| `shared/v1-1-...` (push) | 2026-08-21 14:24 | failure |
| `docs/audit-and-risk-fix` (push) | 2026-08-21 13:19 | failure |
| `main` (PR #1 merge) | 2026-08-21 13:15 | **failure** — merged anyway |
| `chore/rename-and-docs` (push) | 2026-08-21 13:07 | failure |
| `ad/simulator-frontend` (push, today) | 2026-08-23 10:07 | **failure** — "likely failed because of a workflow file issue" |

Two of the three merged PRs (#1, #2) were merged into `main` while their own CI run showed **failure** — this is a live violation of "CI must pass. No direct pushes" as a standing rule, twice, both times by the same author who also owns the CI. Root cause for both: they landed before `.github/workflows/ci.yml` had real content on their branch (the workflow file itself was mid-bootstrap), so GitHub reports "workflow file issue," not a real test/lint failure — not malicious, but the rule was still not honored as written, twice, without a note in `DECISION_LOG.md` explaining the override. `main`'s current tip (PR #3) is green.

Today's `ad/simulator-frontend` CI failure is a different, more serious cause — see §2.

---

## 2. Cross-branch divergence

### Stop-the-line: `shared/` is not frozen

The instruction was to check this first, and it's the finding that matters most in this entire audit.

**`shared/` has been modified outside `main` since the freeze.** `origin/ad/simulator-frontend` (Adhya, pushed 2026-08-23 15:37, today) carries a **complete, independent rewrite** of all four treaty files — `shared/constants.py`, `shared/contracts.py`, `shared/enums.py`, `shared/reason_codes.py` — built from the 17 August empty scaffold, with **zero awareness** that `shared/` v1.0 (19 Aug) or v1.1 (21 Aug, the frozen version) ever existed. This is not a small drift; it is a different product design wearing the same file names:

| | `main` (frozen v1.1, `SCHEMA_VERSION="1.1"`) | `ad/simulator-frontend` (today) |
|---|---|---|
| Style | Plain `dataclass(frozen=True, slots=True)` — no Pydantic, by explicit design (ADR-0005: keeps the trust engine stdlib-only) | Pydantic v2 `BaseModel` throughout |
| Autonomy model | 5-rung ladder, `AUTONOMY_LADDER=(500,1000,2500,5000,10000)`, `rung_of()`/`limit_of()` | 3-tier table, `TIER_LIMITS={"low":5000,"medium":20000,"high":50000}` × `CATEGORY_LIMIT_OVERRIDES` |
| Enums | `Action`, `AgentState`, `DriftSeverity`, `Direction`, `RecommendationStatus`, `OpinionVerdict`, `ReviewVerdict` (7) | `InvoiceCategory`, `SimulationPhase`, `AgentDecision`, `AutonomyTier`, `ApprovalStatus`, `DriftDirection` (6) — **zero names in common** |
| Core decision record | `DecisionRecord` (frozen dataclass, `decision_id`/`sequence`/`invoice_id`/`amount`/`action`/`ground_truth`/...) | `AgentDecisionRecord` (Pydantic) — different name, different fields |
| Reason codes | 18 `UPPER_SNAKE` constants about *why the autonomy ladder moved* (`INSUFFICIENT_SAMPLE`, `CLAWBACK_DRIFT`, ...) | 13 `lower_snake` constants about *why an invoice was approved/rejected* (`approve_within_limit`, `reject_exceeds_limit`, ...) — **zero names in common** |
| Wilson bound | Lives only in `trust/trust_engine/stats/wilson.py` | **Reimplemented from scratch** in `simulator/simulator/runner.py:56`, `def wilson_lower_bound(correct, total, z=WILSON_Z)` — using `shared.constants.WILSON_Z`, a constant that doesn't exist in `main`'s `shared/constants.py` |

Verified with `git merge-tree origin/main origin/ad/simulator-frontend`: merging this branch into `main` **right now** produces real, unresolvable conflicts in exactly 5 files: `.env.example`, `shared/constants.py`, `shared/contracts.py`, `shared/enums.py`, `shared/reason_codes.py`. (`.github/workflows/ci.yml`, `Makefile`, `docker-compose.yml`, `README.md` do *not* conflict — Adhya's branch never touched them, so `main`'s versions win cleanly. This is why her branch's own CI run failed with "workflow file issue": her copy of `.github/workflows/ci.yml` is a **0-byte empty file**, byte-identical to the pre-bootstrap scaffold state, so nothing in it is valid YAML to run.)

**Which lanes break if this merges as-is:**
- **Trust** (`trust/trust_engine/`): every function signature takes `shared.contracts.DecisionRecord` and `shared.enums.Action`. Neither exists after this merge — `AgentDecisionRecord` and `AgentDecision` do instead. `trust/tests/conftest.py` would fail to import immediately, the same `ImportError` failure mode the 21 Aug audit found on `uk/trust` before its own contracts merge (see baseline §5) — this would be that exact failure mode, recurring, self-inflicted, two days after it was fixed.
- **The Policy Engine (backend, not yet built)**: would be built against a 5-rung ladder that this branch has already replaced with a 3-tier table in the one place (`shared/constants.py`) it's supposed to be canonical.
- **Governance (not yet built)**: has nothing to consume — `Recommendation`/`AgentOpinion` (the v1.1 types governance's own lane doc says to build against) don't exist in this branch's `shared/contracts.py` at all.
- **The frontend half of this same branch**: `frontend/src/types/api.ts` is hand-mirrored from *this* version of `shared/contracts.py` ("TypeScript types mirroring shared/contracts.py Pydantic models"), so the frontend and the rest of the system would also disagree the instant real integration starts.

This did not happen because someone edited a frozen file with intent — it happened because this branch's base (`c126543`, 17 Aug) predates `shared/` having any content at all, and 6 days / 14 commits of team decisions (the entire `shared/` v1.0 and v1.1 design, the ladder, the reason-code vocabulary, three ADRs) were never pulled in before ~35,000 lines were built on top of the empty scaffold. Nothing indicates malice or a deliberate decision to diverge — it reads as a large body of work built in isolation, quite possibly by an AI assistant given a self-contained brief and no access to the current `shared/`, `docs/adr/`, or `docs/CONTEXT.md`. But the effect is the same as if the freeze had been violated on purpose: **there are now two incompatible definitions of what an invoice decision, an autonomy limit, and a reason code are**, and one of them has 35,585 lines built on top of it.

### Pairwise overlap between unmerged branches

Only two branches carry real, unmerged content: `origin/ad/simulator-frontend` and `origin/docs/audit-and-risk-fix`. They touch disjoint files — the latter only touches `docs/RISKS.md` and adds `docs/audits/2026-08-21-pre-merge-audit.md`; the former never touches `docs/` at all. **No pairwise conflict between the two unmerged branches themselves.** The conflict that matters is each of them against `main` (§1), and overwhelmingly the `ad/simulator-frontend` one.

---

## 3. What actually exists per lane

### `shared/` — on `main`, frozen v1.1

| File | Lines | Purpose |
|---|---:|---|
| `shared/constants.py` | 68 | Autonomy ladder, schema version, sampling-rate-by-rung, `rung_of`/`limit_of`/`sampling_rate_of` |
| `shared/contracts.py` | 275 | 10 frozen dataclasses: `DecisionRecord`, `ProportionResult`, `ScoreComponent`, `AgentContext`, `DriftResult`, `TrustEvaluation`, `AgentOpinion`, `Recommendation`, `AuditSample` |
| `shared/enums.py` | 74 | 7 `str` enums: `Action`, `AgentState`, `DriftSeverity`, `Direction`, `RecommendationStatus`, `OpinionVerdict`, `ReviewVerdict` |
| `shared/reason_codes.py` | 65 | 18 reason-code constants + `HUMAN_READABLE` dict + `describe()` |

Status vs. deliverables: **DONE** — `shared/` v1.1 merged 2026-08-21 (`docs/DECISION_LOG.md:27-50`), matches the Sat 22 Aug deadline.

### `trust/` — on `main`

| File | Lines | Purpose | Branch |
|---|---:|---|---|
| `trust/pyproject.toml` | 33 | package config, `dependencies=[]` (numpy/scipy removed per RISKS.md R7) | main |
| `trust/trust_engine/constants.py` | 46 | lane-local tunables incl. 4 still-dead ladder constants | main |
| `trust/trust_engine/stats/wilson.py` | 90 | `wilson_interval` (:40), `wilson_lower_bound` (:79) | main |
| `trust/trust_engine/stats/rates.py` | 107 | `partition` (:44), `accuracy` (:63), `utilization` (:71), `human_agreement` (:78), `error_breakdown` (:102) | main |
| `trust/trust_engine/stats/drift.py` | 163 | `split_history` (:38), `two_proportion_z` (:59), `critical_errors_in_window` (:84), `detect_drift` (:94) | main |
| `trust/trust_engine/score.py` | 132 | `ScoreResult` (:55, **local, non-contract shape**), `critical_error_penalty` (:62), `compute_trust_score` (:71) | main |
| 6 test files | 826 | 113 tests | main |

Status vs. `docs/DEADLINES.md`:

| Deliverable | Due | Status | Evidence |
|---|---|---|---|
| Wilson confidence bounds | (part of Wed 26 Aug batch) | **DONE** | `trust/trust_engine/stats/wilson.py:40-90`, cross-validated vs. `statsmodels` |
| Accuracy / human agreement / drift / score | (part of Wed 26 Aug batch) | **DONE** | `rates.py`, `drift.py`, `score.py` as above, 113 passing tests (see §7) |
| `evaluate(decisions, context) -> TrustEvaluation` | Wed 26 Aug | **MISSING** | `grep -rn "def evaluate" trust/` → 0 hits. Not late — due in 3 days, correctly not yet started |
| Autonomy ladder / cooldowns / clawback | Wed 26 Aug | **MISSING** | `trust/trust_engine/constants.py:27-28,43-44` define `MIN_SAMPLE_FOR_INCREASE`, `MIN_TRUST_SCORE_FOR_INCREASE`, `COOLDOWN_BETWEEN_INCREASES`, `CLEAN_DECISIONS_AFTER_CLAWBACK`; `grep -rn` for each outside `constants.py` → 0 hits. Same gap the 21 Aug audit found, unchanged |
| Retire local `ScoreResult` | Wed 26 Aug | **MISSING** | `trust/trust_engine/score.py:55,71,122` — `compute_trust_score()` still returns `ScoreResult`, never `TrustEvaluation` |
| All 15 (now 18) reason codes reachable, one test each | Wed 26 Aug | **MISSING** — 3 of 18 reachable | Only `NO_ACTED_DECISIONS`, `AGREEMENT_EVIDENCE_INSUFFICIENT`, `WEIGHTS_RENORMALISED` are referenced (`trust/trust_engine/score.py:34-36,86,90,108`) |

Not a red flag on its own — this is all Wed 26 Aug work, and today is 23 Aug. Flagged here so §9/§10 can size the work accurately.

### `backend/` — on `main`, and on `origin/vp/backend` (identical)

| File | Lines | Purpose |
|---|---:|---|
| `backend/app/__init__.py`, `api/__init__.py`, `api/v1/__init__.py`, `models/__init__.py`, `observability/__init__.py`, `policy/__init__.py`, `services/__init__.py`, `tasks/__init__.py` | 0 each | empty package markers |
| `backend/alembic/versions/.gitkeep`, `backend/tests/.gitkeep`, `backend/app/api/v1/.gitkeep`, and 5 more `.gitkeep` files | 0 each | directory placeholders |

**Status: STUB in the strictest sense — not even a stub that raises `NotImplementedError`, just empty files.** `grep -rn "NotImplementedError" backend/` → 0 hits, because there is no function to raise it from. Zero lines of actual code. No `main.py`, no `openapi.json`. This directly fails today's deadline — see §9/§10.

### `governance/` — on `main`, and on `origin/vc/governance` (identical)

| File | Lines | Purpose |
|---|---:|---|
| `governance/governance/__init__.py`, `governance/governance/agents/__init__.py` | 0 each | empty package markers |
| `governance/governance/agents/.gitkeep`, `governance/governance/prompts/.gitkeep`, `governance/recordings/.gitkeep`, `governance/tests/.gitkeep` | 0 each | directory placeholders |

**Status: identical situation to backend — zero code, zero commits since the 17 Aug scaffold.** `vc/langgraph-skeleton` was due 24 Aug (tomorrow); nothing has been branched or started yet as of this audit.

### `simulator/` + `frontend/` — **empty on `main`**, real content only on unmerged `origin/ad/simulator-frontend`

On `main`: same pattern as backend/governance — `.gitkeep`/empty `__init__.py` only, 0 lines.

On `origin/ad/simulator-frontend` (unmerged, conflicts with main, built against a stale `shared/` — see §2):

| File | Lines | Purpose |
|---|---:|---|
| `simulator/pyproject.toml` | 29 | deps: `typer`, `httpx`, `pydantic`, **`google-generativeai`**, `python-dotenv`, `rich` |
| `simulator/simulator/agents/base.py` | 56 | agent protocol interface |
| `simulator/simulator/agents/scripted.py` | 146 | rule-based governed agent (no LLM) |
| `simulator/simulator/agents/cache.py` | 145 | cached-LLM-response agent |
| `simulator/simulator/agents/llm.py` | 242 | **live Gemini-calling governed agent** |
| `simulator/simulator/api_client.py` | 154 | HTTP client for posting decisions to the (nonexistent) backend |
| `simulator/simulator/cli.py` | 318 | Typer CLI entry point |
| `simulator/simulator/distributions.py` | 167 | invoice amount/category distributions per phase |
| `simulator/simulator/generator.py` | 317 | synthetic invoice generator |
| `simulator/simulator/labeller.py` | 144 | ground-truth labeller |
| `simulator/simulator/runner.py` | 176 | simulation runner — **reimplements `wilson_lower_bound()` at line 56** |
| `simulator/fixtures/{good,degraded,recovery}.json` | 4,206 / 4,308 / 4,229 | committed deterministic fixtures for the 3 phases |
| 5 simulator test files | 1,204 | 97 tests, all passing (verified — see §7) |
| `frontend/src/app/{agents,agents/[id],approvals,audit,simulation}/page.tsx` | 164/286/163/210/222 | the 5 required routes |
| `frontend/src/components/charts/{AccuracyGauge,AutonomyTimeline,HorizontalThresholdGauge}.tsx` | 80/241/81 | custom gauge components (not the Recharts Area+Line band the lane doc specifies — see below) |
| `frontend/src/components/domain/{ApprovalRow,AutonomyLadder,InvoiceCard}.tsx` | 99/46/73 | domain widgets |
| `frontend/src/lib/{api-client,query-client}.ts`, `frontend/src/mocks/{browser,data,handlers}.ts` | 165/33/11/169/117 | typed fetch client + MSW mocking |
| `frontend/src/types/api.ts` | 176 | **hand-written** TS types "mirroring shared/contracts.py" — not generated from an OpenAPI spec (none exists) |
| `frontend/nexttemp/**` | ~7,000 (mostly `package-lock.json`) | **leftover default `create-next-app` scaffold** — see §4 |

Status vs. `docs/lanes/ad.md` / `docs/DEADLINES.md` (evaluated against what exists on the branch, since none of it is on `main`):

| Deliverable | Due | Status on branch | Evidence |
|---|---|---|---|
| Next.js + TS + Tailwind + **shadcn/ui** scaffolded | 24 Aug | **PARTIAL** | Next.js/TS/Tailwind present (`frontend/package.json`); shadcn/ui is **absent** — `grep -i shadcn frontend/package.json` → 0 hits, despite ad.md listing it as a fixed-stack requirement |
| Types + MSW from `backend/openapi.json` | 24 Aug | **PARTIAL, wrong source** | MSW handlers exist (`frontend/src/mocks/handlers.ts`), but types are hand-written against Adhya's own `shared/contracts.py`, not generated from any OpenAPI file — none exists yet anywhere in the repo (today's backend deadline is also missing, see below) |
| 5 routes rendering with mock data | 24 Aug | **DONE** (on the branch) | all 5 route files present and build successfully (verified — §7) |
| Agent detail + approvals, mandatory reason field | 28 Aug | **PARTIAL, early** | `approvals/page.tsx` and `ApprovalRow.tsx` exist; not due for 5 more days, ahead of schedule but unmerged |
| Wilson band, "the single most valuable visualisation" (Area+Line, narrowing as n grows) | 1 Sept | **NOT MET AS SPECIFIED** | `AccuracyGauge.tsx` renders a single circular ring driven by a pre-computed `wilsonLB` prop, not a Recharts `Area`-behind-`Line` band; `AutonomyLadder.tsx` renders 3 hardcoded tiers (₹3,000/₹15,000/₹50,000), not the 5-rung ladder that's the actual product |
| Never hand-write API types | (standing rule) | **VIOLATED** | `frontend/src/types/api.ts:1-10`, own header admits it: "TypeScript types mirroring shared/contracts.py Pydantic models" |

Simulator deliverable (`uk/simulator`, due 1 Sept, ownership transfers to Utkarsh 27 Aug): substantial real work already exists on this branch under Adhya's authorship, built 4 days before the ownership handover and before `uk/simulator` as a branch exists. Whether this transfers, gets rebuilt, or gets salvaged is a decision for the team, not something this audit can resolve — flagged in §9/§10.

### 0-byte / near-empty tracked files

Every `.gitkeep` and package-marker `__init__.py` in `backend/`, `governance/`, `frontend/src/*`, `simulator/`, `trust/tests/__init__.py`, `trust/trust_engine/__init__.py`, `trust/trust_engine/stats/__init__.py` is 0 bytes — 24 files total on `main`, all intentional placeholders, not defects. Distinct from these: `simulator/fixtures/.gitkeep` on `ad/simulator-frontend` is a **leftover** placeholder sitting alongside 3 real, non-empty fixture files in the same directory — safe to delete, no longer serves a purpose.

---

## 4. Fluff and dead weight

| Item | Evidence | Remove? |
|---|---|---|
| `frontend/nexttemp/` (entire directory, ~7,000 lines, mostly `package-lock.json`) | Default `create-next-app` scaffold output, unmodified (`frontend/src/app/page.tsx` inside it is the stock "Get started by editing..." template). Root `frontend/package.json` itself is still named `"nexttemp"` — confirms this is throwaway scaffold that leaked into the commit, not intentional structure. **Concretely breaks `tsc --noEmit`** (`nexttemp/src/app/layout.tsx(20,50): error TS2304: Cannot find name 'LayoutProps'`) — verified by running `npx tsc --noEmit` in an isolated worktree; the error disappears entirely once `nexttemp/` is set aside, and the real app has zero type errors | **Safe** — on the `ad/simulator-frontend` branch, not merged, but should not be merged as-is |
| `infra/grafana/.gitkeep`, `infra/prometheus/.gitkeep` | On `main`, from the original 17 Aug scaffold. `docker-compose.yml:3-5` (added 21 Aug) explicitly states: *"No Redis, no Celery, no observability stack (Prometheus/Grafana) — cut from scope for the capstone timeline. Do not add them back without an ADR."* The directories were never cleaned up after that explicit decision | **Safe** — dead scaffold for an explicitly cut feature, no ADR references them, nothing reads them |
| `simulator/fixtures/.gitkeep` (on `ad/simulator-frontend`) | Sits next to 3 real fixture files in the same directory | **Safe**, low priority |
| `frontend/package.json` `name: "nexttemp"` | Root frontend package, not the throwaway one, still carries the scaffold's default name | **Safe** rename, cosmetic only |
| `COOLDOWN_BETWEEN_INCREASES`, `CLEAN_DECISIONS_AFTER_CLAWBACK`, `MIN_SAMPLE_FOR_INCREASE`, `MIN_TRUST_SCORE_FOR_INCREASE` (`trust/trust_engine/constants.py:27-28,43-44`) | Defined, referenced nowhere else (`grep -rn` for each name outside `constants.py` → 0 hits) | **Blocked, not fluff** — these are the ladder's tuning knobs, due to be wired up by 26 Aug. Do not delete |
| 15 of 18 reason codes in `shared/reason_codes.py` | `INSUFFICIENT_SAMPLE`, `COOLDOWN_ACTIVE`, `TRUST_BELOW_THRESHOLD`, `AT_MAX_RUNG`, `DRIFT_ACTIVE`, `CLAWBACK_RECOVERY_PENDING`, `EVIDENCE_SUFFICIENT`, `NO_DRIFT_DETECTED`, `NO_RECENT_CRITICAL_ERRORS`, `COOLDOWN_SATISFIED`, `CLAWBACK_DRIFT`, `CLAWBACK_CRITICAL_ERROR`, `SAMPLE_EVIDENCE_INSUFFICIENT`, `RECOMMENDATION_CLAMPED`, `SAMPLE_REVIEW_DISAGREEMENT` never emitted by any code | **Blocked, not fluff** — same as above, waiting on the ladder implementation and, for the last 3, on backend audit-sampling (2 Sept) |
| `AgentContext` (`shared/contracts.py:114-121`) | Never imported anywhere in `trust/` (`grep -rn "AgentContext" trust/trust_engine/` → 0 hits) | **Blocked** — waits on the same `evaluate()` orchestrator |
| `Recommendation`, `AgentOpinion`, `AuditSample` (`shared/contracts.py`, added in v1.1) | Not consumed anywhere — `governance/` and `backend/` are both empty | **Blocked** — this is expected 2 days after the types were added and before either consuming lane has started |
| Banned-tech repo scan (Celery, Redis, Prometheus, Grafana, OpenTelemetry, Jaeger, MLflow, MinIO, S3, WebSockets, Kubernetes) | On `main`: every hit is either an explicit "we don't use this" doc/comment (`docker-compose.yml:3-5`, `docs/CONTEXT.md:58`, `docs/adr/0001...md:30`) or a substring false positive (`redistribut(ed/ion)` in `trust/`). On `ad/simulator-frontend`: one hit, `frontend/src/lib/query-client.ts:13`, `// 2-second polling matches spec (no WebSocket)` — also a deliberate "we're not doing this" comment | **Nothing live to remove** beyond the `infra/` directories above |
| Old project name ("TrustIssues") | One occurrence repo-wide: `docs/audits/2026-08-21-pre-merge-audit.md:1` (`# TrustIssues Pre-Merge Audit`), on the unmerged `docs/audit-and-risk-fix` branch. `chore/rename-and-docs`'s own commit message (`03358a1`) records a deliberate repo-wide search that found this exact occurrence and left it untouched as a dated historical snapshot | **Correctly left alone** — not fluff, an intentional decision already made and documented |
| `trust/pyproject.toml` numpy/scipy deps | Already removed (RISKS.md R7, `docs/DECISION_LOG.md:15-20`) | Already done, nothing to report |
| Simulator ruff hygiene | `uv run ruff check .` on `ad/simulator-frontend`'s `simulator/` → **92 errors, 60 auto-fixable** (mostly import ordering — `I001`). Not currently caught by CI: `.github/workflows/ci.yml` lints `trust/ backend/ governance/` only, never `simulator/` | Not fluff to *remove*, but a gap: CI doesn't cover this lane at all yet |

---

## 5. Boundary violations

### `trust/` — clean

`grep -rn` for every forbidden import (`fastapi`, `sqlalchemy`, `psycopg`, `redis`, `celery`, `import requests`, `httpx`) across `trust/trust_engine/` → 0 hits. Full import list, every file: `__future__`, `math`, `dataclasses`, `typing.Final`/`Sequence`/`collections.abc.Sequence`, `shared.*`, `trust_engine.*`. No `open(`, no `os.environ` reads, no `datetime.now()`/`time.time()`, no `global` statements in engine code (the sole mutable module state anywhere under `trust/` is `_seq = itertools.count()` in `trust/tests/conftest.py`, a test-fixture ID counter — test code, not engine code, not a violation). **No genuine violations.**

### `governance/` — nothing to check

Empty. No imports exist to violate anything.

### `frontend/` (on the unmerged `ad/simulator-frontend` branch — main's `frontend/` is empty)

- **Hand-edited API types**: `frontend/src/types/api.ts:1-10` — its own header states these are hand-mirrored from `shared/contracts.py`, not generated from `backend/openapi.json`. Directly contradicts `docs/lanes/ad.md`'s explicit rule: *"Do not hand-write API types; they are generated from `backend/openapi.json`."* **Genuine violation**, though understandable given no OpenAPI file exists yet (see §9) — still needs remediation, not just an excuse.
- **Borderline business logic**: `frontend/src/components/charts/AccuracyGauge.tsx:14-19` computes `isHealthy = wilsonLB >= threshold` (default `threshold = 0.85`) client-side. This is a judgment call about whether the agent is "healthy," made in TypeScript from a hardcoded threshold, not a value read from the API. Milder than computing a trust score outright, but it is exactly the kind of "the UI computes its own version of the truth" case `ad.md` warns against. **Worth a second look**, not a severe violation — flagged, not overstated.
- No `trust_score`, `eligibility`, or `rung_of`-equivalent computation found anywhere in `frontend/src/`.

### Cross-lane directory writes

`git diff -M --summary` for every commit shows the entire repo's history was authored either by "Varun" (repo owner, cross-cutting scaffold/infra/docs commits — legitimate, that's the team-lead role) or by the named lane owner writing only into their own lane (`UtkarshSahgal` → `trust/` and `shared/`; `Adhya Sharma` → `frontend/`, `simulator/`, and (see §2) `shared/`). **The one boundary violation here is exactly the `shared/` one already covered in §2**: Adhya's branch rewrites 4 files in `shared/`, a directory she does not own and that's supposed to require all-four sign-off. No lane has written into another lane's *directory* (`backend/`, `governance/`, `trust/` are all untouched by anyone but their owners or the team lead's scaffold commit).

---

## 6. Contract consistency

*(All of `shared/`'s types as they exist on `main`, the only version that matters for "consistency" — the parallel version on `ad/simulator-frontend` is covered exhaustively in §2 and isn't a second legitimate contract, it's the divergence itself.)*

| Type | Produced by | Consumed by | Notes |
|---|---|---|---|
| `DecisionRecord` | Simulator (not yet built on `main`) | `trust/trust_engine/stats/*.py` (all of `rates.py`, `drift.py` take `Sequence[DecisionRecord]`) | Consumer exists, producer doesn't yet — expected pre-integration state |
| `ProportionResult` | `trust/trust_engine/stats/rates.py` (`accuracy`, `utilization`, `human_agreement`) | Nothing yet — no backend/frontend to receive it | Correctly matches the contract shape |
| `ScoreComponent` | `trust/trust_engine/score.py:71` (inside `compute_trust_score`) | Nothing yet | matches |
| `AgentContext` | Meant to be supplied by the backend | **Consumed nowhere** — `grep -rn "AgentContext" trust/trust_engine/` → 0 hits | Defined but unconsumed; blocked on the ladder orchestrator, not dead |
| `DriftResult` | `trust/trust_engine/stats/drift.py:94` (`detect_drift`) | Nothing yet | matches |
| `TrustEvaluation` | **Nothing constructs one** — `grep -rn "TrustEvaluation(" trust/trust_engine/` → 0 hits | Nothing yet | The contract's central output type has no producer. Confirmed unchanged from the 21 Aug baseline |
| `Recommendation` / `AgentOpinion` | `governance/` (not started) | `backend/` (not started) | Both sides empty — too early to assess |
| `AuditSample` | `backend/` (not started, due 2 Sept) | `backend/` review queue (not started) | Too early to assess |

**Has `ScoreResult` recurred as a second local duplicate of a shared type?** The exact same one instance the 21 Aug audit flagged is still present, unfixed: `trust/trust_engine/score.py:55` (`class ScoreResult`), returned by `compute_trust_score()` at line 122. It duplicates part of `TrustEvaluation` under a different field name (`renormalised` vs. the contract's `weights_renormalised`) and is missing `agent_id`, the ladder fields, and `drift`. **No new instance of this pattern was found** elsewhere in the `main` codebase — this is the same known issue, not a recurrence, and it's scheduled to be retired by 26 Aug per the ladder deliverable.

**Do the documented invariants hold in code?**
- `rung_of(current_limit) == current_rung`: **Not checked anywhere** — `TrustEvaluation` is a frozen dataclass with no `__post_init__` validation, and nothing constructs an instance yet to test the invariant against. The docstring (`shared/contracts.py:152-156`) explicitly says the dataclass "cannot enforce that itself" and defers responsibility to "whatever constructs a `TrustEvaluation`" — which is nothing, today.
- `eligible_for_increase` / `direction` relationship: same situation — documented precisely (`shared/contracts.py:143-150`: `direction == INCREASE` implies `eligible_for_increase == True`, but not the reverse), enforced nowhere, because nothing produces either field yet.

Both invariants are correctly *specified* and currently *vacuously unverifiable* rather than violated — there's no code yet that could violate them. This is the exact gap the 26 Aug ladder deliverable exists to close; flag it again if it's still unenforced after that date.

---

## 7. Tests and CI

### `trust/` (the only lane with tests on `main`)

```
python -m pytest trust/ -q
```
Ran successfully: **113 passed** in this environment (0 skipped — `statsmodels` happened to be installed here). On CI, where `statsmodels` is deliberately not installed (`ci.yml` only installs `pytest hypothesis ruff`), the expected result is **112 passed, 1 skipped** — matching the Fri 21 Aug baseline check in `docs/DEADLINES.md` exactly. This is environment-dependent, not a regression.

`ruff check trust/ backend/ governance/` → **All checks passed.**

### `backend/`, `governance/` — no tests exist

`compgen -G "backend/tests/test_*.py"` and the governance equivalent both match nothing. `ci.yml` correctly no-ops both (`echo "...has no test_*.py yet — skipping"`) rather than failing. Nothing to run because nothing to test.

### `simulator/` + `frontend/` (unmerged branch — run in an isolated worktree, not the tracked repo)

- `uv run pytest tests/ -q` → **97 passed**, 0 failed.
- `uv run ruff check .` → **92 errors** (60 auto-fixable, mostly import-order `I001`). Not currently gated by CI (`ci.yml` never lints `simulator/`).
- `npx tsc --noEmit` → **1 error**, entirely inside `frontend/nexttemp/` (the leftover scaffold, §4); **0 errors** once that directory is set aside. The real application's types are clean.
- `npm run build` (Next.js production build) → **succeeds**, all 7 routes build (5 required pages + `/` redirect + `/_not-found`).
- `frontend/package.json` has **no `typecheck` script** at all — `ci.yml`'s frontend job runs `npm run typecheck` unconditionally once `frontend/package.json` exists, which it now would if this branch merged; that step would fail immediately with "Missing script: typecheck," independent of and in addition to the `shared/` merge conflicts in §2.

### Components from §3 with no test at all

Everything in `backend/` and `governance/` (no code exists, so trivially no tests). Within `trust/`, the ladder/cooldown/clawback logic and the `evaluate()` orchestrator — because neither exists yet, not because tests were skipped.

### CI on `main`

Confirmed **green** on the current tip (`gh run list`, PR #3 merge, 2026-08-21 16:22, status `success`). Two earlier merges to `main` (PRs #1 and #2) landed with a **failing** CI run at push time — see §1 for detail; not a currently-open problem since the tip is green, but a process gap worth naming once, not repeating.

### `openapi.json` staleness check — does it work as intended?

The mechanism is correctly written (`.github/workflows/ci.yml`, "backend/openapi.json freshness" step): regenerate via `python -m backend.app.export_openapi`, then `git diff --exit-code backend/openapi.json`, failing the build if anything changed. **It cannot currently be exercised** — `backend/app/main.py` doesn't exist, so the step's own guard (`if [ ! -f backend/app/main.py ]; then echo "...nothing to check"; exit 0; fi`) makes it a no-op every time. The check is well-designed and will do exactly what it's supposed to the moment `backend/app/main.py` exists — but as of today, the Sun 23 Aug deadline that was supposed to make it meaningful (`backend/openapi.json committed`) has not landed, so "does it work" is currently untestable rather than confirmed working.

---

## 8. Docs accuracy

Comparing `docs/CONTEXT.md` and `docs/DEADLINES.md` against what's actually in the repo:

| Claim | Where | Reality | Gap |
|---|---|---|---|
| `shared/` — "Not yet merged to `main`" | `docs/CONTEXT.md:186` | Merged 2026-08-21 19:55, same day, about an hour after this table was written | **Stale** — CONTEXT.md was never touched after the `shared/` v1.1 merge landed |
| "15 machine-readable string constants" in `shared/reason_codes.py` | `docs/CONTEXT.md:120` | 65 lines, **18** constants as of v1.1 (3 added: `SAMPLE_EVIDENCE_INSUFFICIENT`, `RECOMMENDATION_CLAMPED`, `SAMPLE_REVIEW_DISAGREEMENT`) | **Stale count** |
| `shared/contracts.py` types table | `docs/CONTEXT.md:126-134` | Lists `DecisionRecord`, `ProportionResult`, `ScoreComponent`, `AgentContext`, `DriftResult`, `TrustEvaluation` only | **Omits `Recommendation`, `AgentOpinion`, `AuditSample` entirely** — all three exist in the actual frozen v1.1 file this table claims to describe |
| `SCHEMA_VERSION="1.0"` | `docs/CONTEXT.md:112` | Actual value is `"1.1"` (`shared/constants.py:13`) | **Stale** |
| Trust Engine row: "Autonomy ladder, cooldowns, and clawback logic... not yet implemented" | `docs/CONTEXT.md:187` | Still accurate as of today | No gap |
| Simulator + Dashboard row: "Empty directory skeleton... Everything: ... absent" | `docs/CONTEXT.md:190` | True of `main`; **false of reality as a whole** — `origin/ad/simulator-frontend` now has ~35,600 lines of working (if incompatible) simulator + frontend code, pushed the same day this audit runs | **Materially incomplete** — the doc's own convention (used for the Trust Engine row) is to name the branch where real content lives even before it's merged; this row doesn't, because it hasn't been touched since 21 Aug, two days and one very large push ago |
| `docs/README.md:13` — points to `../AUDIT.md` | `docs/README.md` | The actual file is `docs/audits/2026-08-21-pre-merge-audit.md`, and it isn't on `main` at all (§1) | **Stale path**, and the file it points to doesn't exist where it says, on the branch where it says to look |
| `docs/RISKS.md` R1 — "five weeks before the 2026-09-12 deadline" | `docs/RISKS.md:9` (on `main`) | 2026-08-21 to 2026-09-12 is **three weeks**, not five. A fix for exactly this exists (`docs/audit-and-risk-fix`, "correct RISKS.md timeline to three weeks") but is unmerged | **Live, uncorrected inaccuracy on `main` right now**, with an already-written, cleanly-mergeable fix sitting idle |
| Sun 23 Aug (today) — "OpenAPI contract published, all endpoints stubbed, `backend/openapi.json` committed" | `docs/DEADLINES.md:23` | No `backend/openapi.json` anywhere in the repo, on any branch. `backend/app/main.py` doesn't exist | **Today's deadline is missed**, not yet reflected as a slip anywhere (no RISKS.md entry, no DECISION_LOG note) |
| Fri 21 Aug — "`docs/ONBOARDING.md` committed... File exists on main" | `docs/DEADLINES.md:20` | `docs/ONBOARDING.md` does not exist on any branch, ever, in git history | **Never done, never flagged** |
| Sat 22 Aug — "audit committed to `docs/audits/`... Merged" | `docs/DEADLINES.md:22` | The audit exists only on the unmerged `docs/audit-and-risk-fix` branch (§1) | **Not actually merged**, despite the deadline sheet implying it is |
| `docs/lanes/` — ad.md, uk.md, vc.md exist; no `vp.md` | `docs/lanes/` (untracked, see header note) | Backend/VP has no equivalent AI-assistant primer despite being the lane with the most undone work and the most cross-cutting responsibility | **Gap**, not a contradiction — nothing claims a `vp.md` exists, but its absence is conspicuous next to the other three |

---

## 9. Per-person deliverable briefs

### Varun P. (backend, lead)

**What exists today:** Nothing in `backend/` beyond empty `__init__.py`/`.gitkeep` files (`backend/app/{api,models,observability,policy,services,tasks}/__init__.py`, all 0 bytes). Everything you *have* shipped is repo-wide infrastructure, not backend code: `docker-compose.yml`, `Makefile`, `.env.example`, `.gitattributes`, `.github/workflows/ci.yml`, `README.md`, `scripts/*.ps1` (`docs/DECISION_LOG.md:9-25`), plus the entire `docs/` bootstrap (`CONTEXT.md`, ADRs, `DECISION_LOG.md`, `RISKS.md`, `README.md`, `CONTRIBUTING.md`) and the `shared/` v1.1 PR.

**Next deliverable, from `docs/DEADLINES.md`:** Sun 23 Aug (**today**) — "OpenAPI contract published, all endpoints stubbed, `backend/openapi.json` committed, staleness CI check." **Not done.** Then Tue 25 Aug — Alembic migration + seed script.

**What's missing to meet today's deadline, in commit-sized steps, ordered so nothing downstream stays blocked:**
1. `backend/app/main.py` — a FastAPI app instance, even with zero real routes wired up yet. This alone makes the existing (already-correct) CI freshness check start doing its job.
2. Stub route handlers for every endpoint the frontend and simulator will need: decision ingest, agent status, approvals, audit log, audit-review-queue — matching the shapes implied by `shared/contracts.py`'s `DecisionRecord`, `Recommendation`, `AuditSample`. Return canned/empty responses; this deadline only requires the schema to exist, not real logic.
3. `backend/app/export_openapi.py` (referenced by `Makefile:81-86` and `ci.yml` already, doesn't exist yet) — a small script that imports the FastAPI app and writes its OpenAPI schema to `backend/openapi.json`.
4. Run `make openapi`, commit `backend/openapi.json`. This is the file Adhya's lane doc says she should never have had to work without (`docs/lanes/ad.md:62-79`) — she's been blocked on it since 21 Aug and has since built ~7,700 lines of frontend against hand-written types instead (§3/§8).
5. Verify the CI freshness step actually fails on a deliberately stale `openapi.json` once, then fix it — right now the check has never run for real (§7), so its correctness is unverified in practice, only on paper.

**Delete as fluff:** `infra/grafana/.gitkeep`, `infra/prometheus/.gitkeep` (§4) — yours to remove since `infra/` has no other owner and `docker-compose.yml`, which you wrote, already documents that both are cut.

**Blocked by / blocking:** You're not blocked by anyone. Backend not existing is currently the single biggest blocker for governance (no contract endpoint to call), for Adhya (built against invented types instead of your OpenAPI schema), and for the Wed 26 Aug ladder work (nothing to hand `AgentContext` to yet). Also worth resolving personally, not lane-blocking: `docs/ONBOARDING.md` was due 21 Aug and was never created (§8) — no one is blocked by its absence today, but it's an open item with your name on it.

---

### Utkarsh (trust, then simulator from 27 Aug)

**What exists today:** `trust/trust_engine/` — Wilson bounds (`stats/wilson.py:40-90`), accuracy/utilization/human-agreement (`stats/rates.py:44-107`), two-stage drift detection (`stats/drift.py:38-163`), trust-score composition (`score.py:55-132`). 113 tests, all passing. This is real, tested, correct work — the 21 Aug audit verified the math in detail and nothing has regressed.

**Next deliverable, from `docs/DEADLINES.md`:** Wed 26 Aug — `uk/autonomy-ladder`: `evaluate(decisions, context) -> TrustEvaluation`, the ladder, cooldowns, clawback, retire `ScoreResult`, all 18 (doc says 15, actual count is 18 — see §8) reason codes reachable with a test each.

**What's missing, in commit-sized steps, ordered so the orchestrator (which everyone else needs) lands before the finer ladder logic:**
1. Write `evaluate(decisions: Sequence[DecisionRecord], context: AgentContext) -> TrustEvaluation` in a new `trust/trust_engine/evaluate.py` (or similar), wiring together the 5 functions that already exist (`accuracy`, `utilization`, `human_agreement`, `error_breakdown`, `detect_drift`) plus `compute_trust_score`. At this step it can populate every field *except* the ladder ones (`direction`, `recommended_limit`/`rung`, `eligible_for_increase`, most of `reason_codes`) with placeholder/HOLD values — this alone unblocks anyone who needs to call something and get a `TrustEvaluation`-shaped object back.
2. Fold `compute_trust_score`'s output directly into `TrustEvaluation.trust_score`/`.components`/`.weights_renormalised` inside `evaluate()`, and delete `ScoreResult` (`trust/trust_engine/score.py:55`) once nothing constructs it anymore.
3. Implement the increase-eligibility check as its own pure function taking the trust score + `AgentContext`, returning `(eligible: bool, blocking_reason_codes: tuple[str,...])` — the 6-condition gate from `docs/lanes/uk.md:178-186` (sample size, trust threshold, cooldown, max rung, drift, clawback recovery). Test each of the 6 failure paths independently before wiring it into `evaluate()`.
4. Implement the clawback check (drift CONFIRMED/CRITICAL, or a critical error in the recent window) as a second pure function, one rung down, floor-clamped.
5. Wire both into `evaluate()`, assert `rung_of(current_limit) == current_rung` at the top of the function and raise loudly if a caller violates it (the invariant `shared/contracts.py:152-156` documents but can't enforce itself).
6. Add the remaining reason-code emissions and one test per code — you're at 3 of 18 today.

**Delete as fluff:** Nothing in your lane — the 4 "dead" constants (`COOLDOWN_BETWEEN_INCREASES` etc.) are exactly what step 3/4 above wires up, not dead weight to remove.

**Blocked by / blocking:** Not blocked by anyone today. You are the current single point of blockage for backend's Wed-onward work (nothing to call), and by 27 Aug you inherit a second, larger problem: `origin/ad/simulator-frontend`'s simulator code (§2/§3) — 1,700+ lines, 97 passing tests, real fixtures — is built against an entirely incompatible `shared/`. Before you touch `uk/simulator`, get a team decision (not something to decide solo, per your own lane doc's "escalate, don't decide alone" — this is squarely a `shared/`-affecting decision) on whether that work gets rebuilt against the real contracts or discarded in favor of starting `uk/simulator` clean.

---

### Varun C. (governance)

**What exists today:** Nothing. `governance/governance/__init__.py`, `governance/governance/agents/__init__.py` — both 0 bytes. Zero commits since the 17 Aug scaffold (`origin/vc/governance` == `c126543`, identical to the very first commit, 6 days and 14 main-branch commits ago).

**Next deliverable, from `docs/DEADLINES.md`:** Mon 24 Aug (**tomorrow**) — `vc/langgraph-skeleton`: LangGraph workflow, 4 agent nodes (Risk, Performance, Compliance, Audit) + a coordinator, `stub` mode only, zero LLM calls, returns a valid `Recommendation` from canned data.

**What's missing, in commit-sized steps:**
1. Branch `vc/langgraph-skeleton` off `main` (not off the stale local `vc/governance`, which is 14 commits behind and doesn't have `shared/` populated at all — confirm you're branching from a `main` that has the `Recommendation`/`AgentOpinion` types, i.e. after the 21 Aug `shared/` v1.1 merge).
2. `governance/pyproject.toml` — package config, LangGraph + Pydantic (for structured output, per `docs/lanes/vc.md:166`) as deps, matching the pattern `trust/pyproject.toml` already sets.
3. One stub module per agent (`governance/governance/agents/{risk,performance,compliance,audit}.py`) — each a function taking a `TrustEvaluation` and returning a canned `AgentOpinion` (`shared/contracts.py:200-211`), no LangGraph node logic yet, just the shape.
4. Wire the 4 stub agents into an actual LangGraph graph with a coordinator node that aggregates their `AgentOpinion`s into one `Recommendation` (`shared/contracts.py:214-249`) — set `governance_mode="stub"`, `has_dissent` computed from whether opinions disagree.
5. A test that calls the coordinator with a hand-built `TrustEvaluation` fixture and asserts a structurally valid `Recommendation` comes back with zero LLM calls made (mock/assert no network).

**Delete as fluff:** Nothing — there's nothing in your lane yet to have accumulated fluff.

**Blocked by / blocking:** Not blocked by backend — your stub-mode deliverable only needs `TrustEvaluation`, which exists as a contract shape today (§6) even though nothing constructs a real instance yet; build against a hand-written fixture, same as everyone else has to until Utkarsh's `evaluate()` lands (26 Aug). You are currently the reason R6 in `docs/RISKS.md` is open (no human-ruling pipeline exists, so `human_agreement` can never have evidence) — not urgent for tomorrow's stub-mode deadline, but worth knowing it's your lane's gap to eventually close, per that risk's own "owner" column.

---

### Adhya (frontend; simulator until 27 Aug)

**What exists today:** By far the most code in the repo outside `trust/` — but **all of it unmerged, on `origin/ad/simulator-frontend`, and built against a `shared/` you reinvented rather than the one the team froze on 21 Aug** (§2). 82 files, +35,585 lines: a full simulator (`simulator/simulator/{generator,labeller,runner,cli,api_client}.py`, 3 agent implementations including a live-Gemini one, 3 committed fixture sets, 97 passing tests) and a full frontend (5 routes, custom chart components, MSW mocks, a hand-written API type file). It's real, working code — it typechecks clean and builds clean once the leftover `frontend/nexttemp/` scaffold folder (§4) is set aside — but none of it can merge as committed: 5 files conflict outright (`shared/{constants,contracts,enums,reason_codes}.py`, `.env.example`), and your own `.github/workflows/ci.yml` is a 0-byte empty file, which is why today's CI run on your branch failed before a single test ran.

**Next deliverable, from `docs/DEADLINES.md`:** Mon 24 Aug — `ad/frontend-scaffold`, Next.js+TS+Tailwind+shadcn/ui, types+MSW from `backend/openapi.json`, 5 routes with mock data. On the numbers alone this is done and then some — but shadcn/ui was never added, and the types come from your own `shared/contracts.py`, not from an OpenAPI file (which still doesn't exist — not your fault, see Varun P.'s brief).

**What's missing to make what you've already built actually mergeable, in commit-sized steps, ordered so the blocking one comes first:**
1. **Do not build further on this branch's `shared/` files.** Before anything else, get the team's actual `main` — `git fetch && git checkout main && git checkout -b ad/frontend-scaffold-v2` (or similar) — so you're building against the real, frozen `shared/` (5-rung ladder, `DecisionRecord`, the 18 real reason codes) instead of the 3-tier/Pydantic version you built independently.
2. Re-point `frontend/src/types/api.ts` at the real `shared/contracts.py` shapes (`DecisionRecord`, `TrustEvaluation`, `Recommendation`, `AgentOpinion`, `AuditSample`) — this is a full rewrite of that file's type definitions, not a patch, since none of your current enum/type names (`AgentDecision`, `AutonomyTier`, `InvoiceCategory`) exist in the real contracts.
3. Rebuild `AutonomyLadder.tsx` around the actual 5-rung ladder (`₹500 → ₹1,000 → ₹2,500 → ₹5,000 → ₹10,000`, `AUTONOMY_LADDER` in `shared/constants.py`), not the 3-tier ₹3,000/₹15,000/₹50,000 model currently hardcoded into the component — this is your single most important chart per your own lane doc and it currently shows the wrong product.
4. Rebuild the accuracy visualization as a Recharts `Area` (band) behind a `Line` (point estimate) using `ProportionResult.wilson_lower`/`wilson_upper`/`point`, replacing `AccuracyGauge.tsx`'s single-ring design — and drop the client-side `isHealthy = wilsonLB >= threshold` comparison (§5) in favor of a status the backend already computed.
5. Add `shadcn/ui` to `frontend/package.json` and use it for at least the primary interactive surfaces (approvals actions, forms) — currently absent despite being a fixed-stack requirement.
6. Delete `frontend/nexttemp/` entirely and rename the root `frontend/package.json`'s `"name"` away from `"nexttemp"` — this is the one-line fix that makes `tsc --noEmit` pass cleanly (verified — §4/§7).
7. Add a `"typecheck": "tsc --noEmit"` script to `frontend/package.json` — CI's frontend job already calls `npm run typecheck` and will fail on "missing script" the moment this branch's `package.json` is what CI sees.
8. Once your part of `shared/` conflicts (step 1-2) is resolved, restore your branch's `.github/workflows/ci.yml` to match `main`'s real version instead of the 0-byte file currently there.

**Delete as fluff:** `frontend/nexttemp/` (step 6 above — also listed in §4). `simulator/fixtures/.gitkeep`, redundant next to the 3 real fixture files.

**Blocked by / blocking:** You were legitimately blocked on `backend/openapi.json` (never delivered — Varun P.'s deadline, still open) and reasonably worked around it by hand-writing types against your own `shared/contracts.py` — the actual mistake was reinventing `shared/` itself rather than pulling in the version the team had already frozen four days before you built this. You are now the blocker for anyone (Utkarsh, from 27 Aug) who needs to build on top of your simulator work — that handover cannot proceed cleanly until the `shared/` question above is resolved, ideally as a team decision this week rather than something either of you resolves unilaterally, since it touches a frozen treaty file (`CONTRIBUTING.md:10-11`: any `shared/` PR needs all four owners' sign-off).

---

## 10. Critical path

**Three things that most endanger 12 September, in order:**

1. **The `shared/` divergence on `ad/simulator-frontend` (§2).** This is not "a lane is behind," it's "35,585 lines were built against a different product definition than the one the rest of the team is using," discovered on the same day it happened. Every day this goes unresolved, either more gets built on the wrong foundation, or the eventual reconciliation gets more expensive. This is also the thing most likely to consume days of Utkarsh's 27 Aug simulator handover unless it's settled first.
2. **Backend is 6 days old and zero lines of code, with today's deadline (`backend/openapi.json`, due 2026-08-23) already missed.** Every other lane's stated blocker traces back here: governance has nothing to call, Adhya built against invented types because there was nothing real to generate from, and the Wed 26 Aug ladder work has no `AgentContext` producer to integrate with even once it's done. Per ADR-0003, the Policy Engine — backend's job — is "the most consequential absence in the current repo state," and that was already true two days ago; it still is.
3. **The ladder/cooldown/clawback logic (`evaluate()`, due 26 Aug) is the actual product concept and does not exist yet.** The math around it is excellent, but "an AI agent earns autonomy through evidence" is a claim the repo cannot currently demonstrate for a single invoice. This is the least *urgent* of the three (it's not due for 3 more days and is on schedule), but it is the one item on this list that is squarely "the project," not infrastructure around the project — if it slips, there is no fallback demo.

**Cut list from `docs/DEADLINES.md`, re-checked against what this audit found:**

> 1. Live Gemini mode 2. Audit sampling UI 3. RBAC beyond a single role check 4. The simulation console

**Still correct, with one addition worth naming, not adding to the numbered list itself:** none of the four cuts conflict with anything found in this audit — all four are late-Phase-3 items nothing currently depends on. But this audit surfaces a fifth candidate the original list didn't anticipate, because it didn't exist yet: **the `ad/simulator-frontend` branch's independent `shared/` and 3-tier autonomy model should be treated as disposable if reconciling it costs more than a day or two** — i.e., if the team decides Thursday that rebuilding Adhya's frontend against the real contracts (§9, her checklist) is running long, the fallback is not "cut a feature," it's "start `ad/frontend-scaffold-v2` clean against real `shared/` and salvage only the parts that transfer easily (route structure, MSW pattern, the simulator's generator/labeller/fixture logic once ported to real enum names)," rather than sinking further time into reconciling two independently-designed autonomy models. The demo arc, Wilson band, clawback, and approval flow — the four items the deadline sheet calls "not cuttable" — all depend on the *real* ladder, so a frontend built around the wrong one is closer to a rebuild than a fix regardless of how much code exists.
