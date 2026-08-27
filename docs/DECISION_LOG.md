# Decision Log

Reverse-chronological. One entry per change of note (not every commit). Append
new entries at the top. See `docs/README.md` for when to update this vs. an
ADR.

---

**2026-08-27 — Varun P. (via `vp/openapi-contract`)** — Published the complete
backend HTTP contract: `backend/app/main.py`, all eighteen endpoints stubbed
against internally-consistent fixtures (three agents — one mid-ladder and
eligible for an increase, one on probation with a small sample, one clawed
back after confirmed drift), `export_openapi.py`, `backend/openapi.json`
committed. Every response model mirroring a `shared/contracts.py` dataclass
(`DecisionRecord`, `TrustEvaluation`, `DriftResult`, `ProportionResult`,
`ScoreComponent`, `Recommendation`, `AgentOpinion`, `AuditSample`,
`AgentContext`) does so field-for-field, enforced by a generalized
contract-drift test (`backend/tests/test_schema_contracts.py`) rather than
nine hand-written ones. Wrote ADR-0011 for the two decisions made once and
applied everywhere: the `items`/`total`/`page`/`page_size` pagination
envelope, and a mandatory `reason` on every mutating endpoint, including the
two (`POST /decisions`, `POST /simulation/runs`) that don't look like
governance decisions at first glance. No database models, migrations, or
SQLAlchemy anywhere in this branch — persistence is separate work
(docs/DEADLINES.md: Fri 28 Aug onward). **Why:** Tue 25 Aug deliverable,
already two days late (docs/audits/2026-08-27-delta-audit.md); the frontend
lane has been blocked on this file since 21 Aug. **Affects:** `backend/`
only. Also fixed the dev environment while touching it: `make setup` /
`scripts/setup.ps1` now install all four Python lanes (trust, simulator,
governance, backend) editable unconditionally — the old conditional
"install if it exists" logic was written when backend/governance were
empty and silently left simulator out entirely; `make test` runs pytest
across all four; `docs/ONBOARDING.md` updated to match, since "install only
`trust[dev]`" left simulator and governance tests failing on import with no
obvious cause for anyone following it literally.

**2026-08-27 — Varun (via `docs/resurrect-pr5`)** — Re-applied PR #5's commit
(`6a77eed`, "transplant Wilson table, ADR defend-it lines, layer walkthrough
into SYSTEM-EXPLAINED.md"), cherry-picked cleanly onto `main` as `7a169f6`.
**Why:** PR #5 was opened with base `docs/reset-and-reschedule` instead of
`main`. PR #4 (`docs/reset-and-reschedule` → `main`) merged at
2026-08-23T13:15:55Z; PR #5 merged its commit into `docs/reset-and-reschedule`
32 seconds later, at 13:16:27Z — by which point that branch had already done
its one job and nobody opened a follow-up PR to carry the new commit into
`main`. GitHub shows PR #5 as `MERGED`, and it was, into a branch that never
reached `main` — `origin/docs/reset-and-reschedule` still exists, still
sitting at that commit, four days later. Content was verified missing
(`git merge-base --is-ancestor 6a77eed origin/main` → false) and restorable
without conflict (`main`'s `docs/SYSTEM-EXPLAINED.md` was still byte-identical
to `6a77eed`'s parent, so nothing on `main` needed reconciling). **Affects:**
`docs/SYSTEM-EXPLAINED.md` only — the Wilson lower-bound numbers table, a
"Defend it" line on all 10 ADRs, and the plain/technical layer-by-layer
walkthrough are back; verified in `docs/audits/2026-08-27-delta-audit.md` §1
and the PR that carries this entry. `docs/RISKS.md`/`docs/CONTEXT.md`'s own
staleness (unrelated to this gap) is not addressed here.

**2026-08-24 — Varun C. (via `vc/langgraph-skeleton`)** — Set governance's
default mode to `stub`, not `cached`. `resolve_mode()` raises `ValueError` on
an unrecognised mode rather than falling back. **Why:** an unset
`GOVERNANCE_MODE` must never reach for a fixture directory that does not exist
yet, and must never be one typo away from a live API call. A mode that
silently degraded to stub would look like a working demo while proving
nothing. **Affects:** anything invoking `governance.recommend()`; `cached`
becomes the demo default explicitly, at the call site, once it exists (30 Aug).

**2026-08-24 — Varun C. (via `vc/langgraph-skeleton`)** — `Recommendation.
trust_evaluation_ref` is supplied by the caller, not generated in governance.
**Why:** `TrustEvaluation` carries no identity field, and the backend is the
only component that persists both sides; minting an id here would produce a
reference pointing at nothing. **Affects:** `vp/backend` — the backend must
pass its own evaluation id into `recommend()`. **Needs Varun P.'s
confirmation**, as it changes the call signature he builds against.

**2026-08-24 — Varun C. (via `vc/langgraph-skeleton`)** — Governance's audit
agent detects unruled escalations and critical-error clustering, but *not* the
per-vendor or time-windowed anomalies described in `docs/lanes/vc.md`.
**Why:** those need `DecisionRecord` history; `TrustEvaluation` carries only
aggregates. Widening the input is a cross-lane contract change and `shared/`
is frozen until 9 Sept (ADR-0005). **Affects:** scope of the audit agent;
revisit via ADR if the wider input is wanted.

**2026-08-23 — Varun (via `docs/reset-and-reschedule`)** — Named Utkarsh
backup reviewer: if Varun P. is unavailable, Utkarsh can approve and merge
anything that doesn't touch `shared/` (which still needs all four owners).
**Why:** Varun P. has interview commitments 24 Aug - 3 Sept and the team
cannot afford a lane sitting blocked on review during that window (RISKS.md
R12). **Affects:** the review process for every lane but `shared/` itself;
documented in `docs/DEADLINES.md` and `docs/lanes/uk.md`.

**2026-08-23 — Varun (via `docs/reset-and-reschedule`)** — Deleted
`infra/grafana/.gitkeep` and `infra/prometheus/.gitkeep`, and the now-empty
`infra/grafana/` and `infra/prometheus/` directories. **Why:** dead scaffold
left over from the 17 Aug initial commit for an observability stack
`docker-compose.yml` already explicitly states is cut from scope ("No Redis,
no Celery, no observability stack (Prometheus/Grafana)"). Flagged in
`docs/audits/2026-08-23-state-audit.md` §4. **Affects:** `infra/` only;
nothing referenced either directory.

**2026-08-23 — Varun (via `docs/reset-and-reschedule`)** — Committed
`docs/DEADLINES.md`, `docs/ONBOARDING.md`, `docs/SYSTEM-EXPLAINED.md`, and
`docs/lanes/{ad,uk,vc,vp}.md` to `main` for the first time. **Why:** all of
these existed only outside git before today. That is the direct, named root
cause (RISKS.md R11, ADR-0010) of ~35,600 lines being built on
`origin/ad/simulator-frontend` against an invented `shared/`, because nobody
who cloned the 17 Aug scaffold could discover the real one existed. A
document that isn't in the repository doesn't exist as far as a fresh clone —
or a fresh clone's AI assistant — is concerned. **Affects:** every lane;
`docs/ONBOARDING.md` now tells anyone joining, or anyone whose local branch
predates 23 Aug, exactly how to catch up.

**2026-08-23 — Varun (via `docs/reset-and-reschedule`)** — Merged the
stranded `origin/docs/audit-and-risk-fix` branch (the RISKS.md three-week
timeline correction and the 2026-08-21 pre-merge audit file), 2 days after it
became mergeable. **Why:** it was clean and conflict-free the entire time —
there was no technical reason for it to sit unmerged; it was simply never
picked up. **Affects:** `docs/RISKS.md`, adds
`docs/audits/2026-08-21-pre-merge-audit.md`.

**2026-08-23 — Varun (via `docs/reset-and-reschedule`)** — Wrote ADR-0010:
`main`'s frozen v1.1 `shared/` contracts are canonical; the divergent design
independently built on `origin/ad/simulator-frontend` is partially ported
(estimated 7-9 person-days per `docs/audits/2026-08-23-port-feasibility.md`),
not merged as-is and not discarded. Submission moved **12 September → 15
September 2026**; feature freeze moved **6 September → 9 September 2026**,
giving the port three extra days of runway it would not otherwise have had.
**Why:** two incompatible definitions of the core domain cannot coexist in a
system whose entire premise is a single auditable source of truth (ADR-0005);
discarding ~5,900 lines of real, working, port-feasible code costs more
(10-13 person-days) than fixing its foundation (7-9). **Affects:** `shared/`,
`simulator/`, `frontend/`; every date in `docs/DEADLINES.md` and
`docs/lanes/*.md`; see ADR-0010 for full reasoning, `docs/RISKS.md` R9 for
the risk this closes down to a scoped, owned, dated piece of work.

---

**2026-08-21 — Varun (via `chore/infra-baseline`)** — Filled in every 0-byte
root-level placeholder: `docker-compose.yml` (postgres:16 + adminer, no
Redis/Celery/observability), `.env.example`, `Makefile`
(setup/up/down/db-reset/test/test-trust/openapi/lint/fmt/dev/frontend, all
skipping gracefully when a lane has no code yet), `.github/workflows/ci.yml`
(same skip-gracefully philosophy, plus an `openapi.json` staleness check),
`.gitattributes`, `README.md`, and `scripts/*.ps1` for teammates without GNU
make. Also fixed 19 pre-existing ruff findings in `trust/` (mechanical only —
import order, `range(0, n)`, one NaN-check inconsistency between two
near-identical `_clamp01` helpers; deliberately did not run `ruff format`,
which would have restyled the author's test-constructor style far beyond
what the findings needed) so the new CI lint step doesn't fail on day one.
**Why:** nothing in the repo ran end to end before this — `docs/DEADLINES.md`
needs a working `make setup && make up` for Phase 2 to start. **Affects:**
every lane; `make setup`/`make test-trust` verified working on this machine
(after fixing a Windows backslash-path bug the first run caught); `make
up`/`down` could not be verified here — no Docker installed on this machine.

**2026-08-21 — Varun (via `shared/v1-1-recommendation-and-audit-sample`)** —
Shipped `shared/` v1.1 (`SCHEMA_VERSION` "1.0" → "1.1"), the Phase 1 deliverable
from `docs/DEADLINES.md`: added `Recommendation` + `AgentOpinion` (governance's
output contract, mirroring `TrustEvaluation`'s role for the trust lane) and
`AuditSample` (the rung-scaled post-hoc review mechanism, ADR-0009) to
`shared/contracts.py`; `RecommendationStatus`, `OpinionVerdict`, `ReviewVerdict`
to `shared/enums.py` (uppercase values, with a comment flagging — not fixing —
`AgentState`'s pre-existing lowercase inconsistency); `SAMPLING_RATE_BY_RUNG`,
`MIN_SAMPLES_FOR_ACCURACY_ESTIMATE`, `sampling_rate_of()` to
`shared/constants.py`; `SAMPLE_EVIDENCE_INSUFFICIENT`, `SAMPLE_REVIEW_DISAGREEMENT`,
`RECOMMENDATION_CLAMPED` to `shared/reason_codes.py`. Documented, as docstrings
on `TrustEvaluation`, the two ambiguities `AUDIT.md` flagged: the
`eligible_for_increase`/`direction` relationship and the
`current_limit`/`current_rung` invariant. Purely additive — no existing field or
type changed; a short list of contract gaps this surfaced (notably: no field
distinguishing ground-truth-derived vs. sample-derived accuracy on
`TrustEvaluation`) was handed back for a decision rather than added to the diff.
**Why:** `docs/DEADLINES.md` requires `shared/` to freeze at this merge with all
four lane owners' approval, and everything downstream of it (governance's
recommendation output, the backend's review queue, the trust engine's
production ground-truth source) is blocked on this contract existing first.
**Affects:** all four lanes — this is the last `shared/` change permitted
before the 6 September feature freeze per the standing rules in
`docs/DEADLINES.md`.

**2026-08-21 — Varun (via `chore/rename-and-docs`)** — Merged
`origin/uk/shared-trust-contracts` and `origin/uk/trust` into
`chore/rename-and-docs` before doing any rename/documentation work, since
those are the only two branches with real content and the trust engine cannot
be discussed, cited, or edited without them. **Why:** the repo-wide rename and
documentation bootstrap referenced files (`trust/pyproject.toml`,
`trust/trust_engine/`) that only exist on `origin/uk/trust`, and that branch
only imports cleanly once `shared/contracts.py` is populated from
`origin/uk/shared-trust-contracts`. **Affects:** this branch now has a working
trust engine + populated `shared/`; `main` itself still does not — that merge
is a separate, still-pending step (see Risk R2 in `docs/RISKS.md`).

**2026-08-21 — Varun** — Commissioned a full pre-merge audit of `uk/trust`
(`AUDIT.md`). Found the branch unmergeable as committed: its copy of
`shared/contracts.py` was still the empty placeholder, because `uk/trust` and
`uk/shared-trust-contracts` diverged independently from the same base commit
and neither was ever merged into the other. Also found the autonomy
ladder/cooldown/clawback logic — half of `uk/trust`'s ownership brief — is
entirely unimplemented (constants defined, nothing reads them), and that no
function anywhere produces the `TrustEvaluation` contract type. **Why:**
pre-merge gate before any lane starts integrating against `uk/trust`.
**Affects:** merge order and the fix checklist for `uk/trust`; directly
motivated the merge above.

**2026-08-20 15:57 (`70b3b96`) — Utkarsh Sahgal** — Pushed `origin/uk/trust`:
Wilson score interval, rate/proportion calculations (accuracy, utilization,
human agreement), two-stage drift detection, trust-score composition, and a
113-test suite. **Why:** `uk/trust`'s ownership brief — the statistical
evidence engine. **Affects:** `trust/` package. Notably does *not* implement
the autonomy ladder or cooldowns despite `trust/trust_engine/constants.py`
already defining their thresholds.

**2026-08-19 17:06 (`5721b1e`) — Utkarsh Sahgal** — Removed placeholder
`.gitkeep` files in `trust/`, replaced by real package contents. **Affects:**
`trust/` directory structure only.

**2026-08-19 17:03:58 (`f606d6a`) — Utkarsh Sahgal** — Added `trust/pyproject.toml`,
package `__init__.py` files, and `DecisionRecord` contract tests. Branched
from `main`, **not** from `uk/shared-trust-contracts` (pushed by the same
author two minutes earlier) — this is the root cause of the later divergence
resolved on 2026-08-21 above. **Affects:** `trust/` package skeleton.

**2026-08-19 17:02:09 (`444fdc0`) — Utkarsh Sahgal** — Pushed
`origin/uk/shared-trust-contracts`: populated `shared/enums.py`,
`constants.py`, `reason_codes.py`, and `contracts.py` — the cross-lane treaty
files, including `TrustEvaluation`, `DecisionRecord`, `AgentContext`,
`DriftResult`, `ProportionResult`, `ScoreComponent`. **Why:** give all four
lanes a common contract to build against (ADR-0005). **Affects:** every lane,
in principle — as of 2026-08-21, only this branch (`chore/rename-and-docs`)
and its own origin branch actually have it; `main` and the other three lane
branches do not yet.

**2026-08-17 23:56:58 (`c126543`) — Varun** — "chore: initialize project
structure": created the four-lane directory skeleton (`backend/`, `trust/`,
`governance/`, `simulator/`, `frontend/`, `shared/`, `infra/`) as empty
placeholder files (`.gitkeep`, empty `__init__.py`, 0-byte config files).
**Why:** establish the four-owner branch structure for the capstone.
**Affects:** baseline for every subsequent lane branch (`vp/backend`,
`uk/trust`, `vc/governance`, `ad/simulator-frontend` all still point at this
exact commit as of 2026-08-21, except `uk/trust`'s origin, per above).
