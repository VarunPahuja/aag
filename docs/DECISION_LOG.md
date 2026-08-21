# Decision Log

Reverse-chronological. One entry per change of note (not every commit). Append
new entries at the top. See `docs/README.md` for when to update this vs. an
ADR.

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
