# CONTEXT.md — Adaptive AI Governance Platform (AAGP)

This is the single source of truth for the project. If you are new to the repo — a
teammate, a mentor, a judge — start here. It is written to require zero prior
context. For the full design, glossary, and every architectural decision
explained, see `docs/SYSTEM-EXPLAINED.md`. Everything in this file is checked
against the actual repo state as of **2026-08-23**; where the code doesn't yet
match the intent, that's stated explicitly rather than glossed over.

---

## Problem statement

An AI agent is given the job of approving or rejecting invoices — a task that
moves real money and where a wrong APPROVE is worse than a wrong REJECT. Nobody
wants to hand an untested agent unlimited authority on day one, and nobody wants
to permanently cap a good agent at "approve nothing over $500" once it has
proven itself.

AAGP is an **earned autonomy engine**: the agent starts with a small autonomy
limit (how large an invoice it's allowed to decide on its own) and earns the
right to a higher limit only when there is statistical evidence — not a vibe,
not a self-report — that it is performing well. If its performance degrades,
its limit is clawed back automatically. Every step of that process is meant to
be auditable: a human (or a judge) should be able to ask "why does the agent
have this limit right now?" and get a specific, evidenced answer.

## The core design rule

> **LLM reasons. Statistics provide evidence. Policy Engine enforces. Humans
> authorize.**

Four different kinds of authority are deliberately kept separate:

- **LLM reasons** — the governance agents (Gemini, via LangGraph) read the
  evidence and the situation and produce a human-readable recommendation and
  rationale. They explain; they do not decide.
- **Statistics provide evidence** — the trust engine computes Wilson-bound
  accuracy, human-agreement, drift, and a composed trust score from raw
  decision history. It is pure arithmetic: reproducible, no LLM call, no
  judgment call. It has no ability to *act* on what it computes.
- **Policy Engine enforces** — the backend's policy layer is the only thing
  that actually changes an agent's spending limit or blocks a decision. It is
  deterministic code, not a prompted model, and it is the sole gate between
  "the evidence says X" and "the agent's authority actually changes."
- **Humans authorize** — increasing an agent's autonomy (giving it *more*
  power) requires a human sign-off on the recommendation. Taking autonomy away
  (clawback) does not — see [ADR-0004](adr/0004-human-approval-required-for-autonomy-increases.md).

This separation is why the codebase is split into four independently-owned
lanes instead of one team building one service — see
[ADR-0001](adr/0001-statistical-evidence-not-llm-judgment.md).

## The four lanes

| Lane | Owner | Directory |
|---|---|---|
| Backend | Varun P. (team lead) | `backend/` |
| Trust Engine | Utkarsh | `trust/`. Wilson confidence bounds, accuracy/human-agreement metrics, critical-error weighting, recent-vs-historical drift detection, trust score composition, the autonomy ladder, cooldowns, and tests. **Hard rules**: no FastAPI, no SQLAlchemy/psycopg/DB access, no Redis, no Celery, no network calls. Pure functions wherever possible. Must emit the `TrustEvaluation` contract |
| Governance | Varun C. | `governance/`. LangGraph governance agents, Gemini integration, human-readable recommendations |
| Simulator | Adhya (porting `origin/ad/simulator-frontend` onto real contracts), then Utkarsh | `simulator/`. Synthetic invoice generation with deterministic ground truth |
| Frontend | Adhya | `frontend/`. The Next.js dashboard |

Backend owns Postgres, SQLAlchemy, Alembic, the Policy Engine, API endpoints,
JWT/RBAC, Docker Compose, and wiring the other lanes together.

Cross-lane contracts — the types every lane agrees to use — live in `shared/`
and are governed as a "treaty": see
[ADR-0005](adr/0005-shared-contracts-as-cross-lane-treaty.md) and
`CONTRIBUTING.md`. `main`'s frozen v1.1 `shared/` is the only valid contract
set — see [ADR-0010](adr/0010-main-shared-contracts-canonical.md) for why
that needed saying explicitly.

## End-to-end request flow (intended design)

This is the flow the architecture is built for. As of today, most of it is
**not yet wired up in code** — see Current Status below for what actually
exists.

1. **Simulator** generates a synthetic invoice with a deterministic correct
   answer (`ground_truth: Action`).
2. The governed agent decides `APPROVE` / `REJECT` / `ESCALATE`, constrained by
   its current autonomy limit (a rupee cap), which the **Policy Engine**
   enforces before the decision is allowed to stand.
3. The decision becomes a `DecisionRecord` (`shared/contracts.py`) — this is
   the simulator's output and the trust engine's input.
4. Escalated decisions go to a human reviewer, whose ruling fills in
   `recommended_action` / `human_ruling` on the record.
5. The **Trust Engine** consumes the agent's decision history and current
   standing (`AgentContext`) and computes accuracy, utilization, human
   agreement (all with Wilson lower bounds), critical/non-critical error
   counts, drift status, and a composed `trust_score` — packaged as a
   `TrustEvaluation`.
6. **Governance agents** read the `TrustEvaluation` and produce a
   recommendation with plain-language reasoning — but do not themselves grant
   or revoke anything.
7. The **Policy Engine** applies the recommendation: an *increase* requires a
   human to authorize it; a *clawback* (drift or critical error) is applied
   automatically.
8. The **dashboard** visualizes trust score, autonomy position, drift
   status, and the decision/audit trail.

## Shared contracts (`shared/`)

All four files are marked `TREATY FILE` in their own docstrings — changes
require sign-off from all four lane owners (see `CONTRIBUTING.md`).

### `shared/enums.py`

| Enum | Values |
|---|---|
| `Action(str, Enum)` | `APPROVE`, `REJECT`, `ESCALATE` |
| `AgentState(str, Enum)` | `probation`, `active`, `restricted`, `suspended` |
| `DriftSeverity(str, Enum)` | `NONE`, `WARNING`, `CONFIRMED`, `CRITICAL` |
| `Direction(str, Enum)` | `INCREASE`, `HOLD`, `CLAWBACK` |
| `RecommendationStatus(str, Enum)` (v1.1) | `PENDING`, `APPROVED`, `REJECTED`, `SUPERSEDED` |
| `OpinionVerdict(str, Enum)` (v1.1) | `CONCUR`, `OBJECT`, `ABSTAIN` |
| `ReviewVerdict(str, Enum)` (v1.1) | `AGREED`, `DISAGREED`, `INCONCLUSIVE` |

### `shared/constants.py`

`SCHEMA_VERSION="1.1"`, `CURRENCY="INR"`, `AUTONOMY_LADDER=(500, 1000, 2500,
5000, 10000)`, `AUTONOMY_FLOOR=500`, `MAX_RUNG=4`, `TRUST_SCORE_MIN/MAX=0.0/100.0`,
`CRITICAL_ERROR_DEFINITION` (a critical error is APPROVE-ing an invoice whose
ground truth is REJECT — money leaves the building; the reverse is an error but
not a critical one), `rung_of(limit)` / `limit_of(rung)` helpers, plus (v1.1)
`SAMPLING_RATE_BY_RUNG=(1.0, 0.50, 0.25, 0.10, 0.05)`,
`MIN_SAMPLES_FOR_ACCURACY_ESTIMATE=20`, and a `sampling_rate_of(rung)` helper
for post-hoc audit sampling (ADR-0009).

### `shared/reason_codes.py`

18 machine-readable string constants (increase-blocked reasons, increase-allowed
reasons, clawback reasons, evidence-quality notes, and — new in v1.1 —
audit-sample findings) plus a `HUMAN_READABLE` dict and a `describe(codes)`
formatter — the rule is the human-readable sentence is always generated
*from* a code, never written free-hand.

### `shared/contracts.py`

| Type | Fields |
|---|---|
| `DecisionRecord` | `decision_id`, `sequence`, `invoice_id`, `amount`, `action`, `ground_truth`, `agent_id="agent-01"`, `decided_at=None`, `recommended_action=None`, `human_ruling=None`, plus computed properties `is_escalated` / `is_acted` / `is_correct` / `is_critical_error` / `is_noncritical_error` / `has_human_ruling` / `human_agreed` |
| `ProportionResult` | `successes`, `trials`, `point`, `wilson_lower`, `wilson_upper` |
| `ScoreComponent` | `name`, `value`, `nominal_weight`, `effective_weight`, `available` |
| `AgentContext` | `current_limit=AUTONOMY_FLOOR`, `decisions_since_last_change=0`, `decisions_since_clawback=None`, `state=PROBATION` — the agent's standing, supplied by the backend |
| `DriftResult` | `severity=NONE`, `detected=False`, `recent_accuracy`, `baseline_accuracy`, `drop_pp`, `z_statistic`, `p_value`, `critical_errors_in_window=0`, `recent_n=0`, `baseline_n=0`, `underpowered=False` |
| `TrustEvaluation` | The complete engine output: identity/versioning, decision counts, the three `ProportionResult`s, error counts, `trust_score` + `components` + `weights_renormalised`, `drift`, ladder position (`current_limit/rung`, `recommended_limit/rung`, `direction`, `eligible_for_increase`), `state`, `reason_codes`, `evaluated_at`, `config_fingerprint` |
| `AgentOpinion` (v1.1) | One governance agent's stance before opinions combine into a `Recommendation`: `agent_name`, `verdict` (`OpinionVerdict`), `reasoning`, `concerns`, `confidence` |
| `Recommendation` (v1.1) | Governance's complete output, mirroring `TrustEvaluation`'s role for the trust lane: `recommendation_id`, `agent_id`, `direction`, `proposed_limit`/`proposed_rung`, `rationale`, `opinions: tuple[AgentOpinion, ...]`, `has_dissent`, `confidence`, `governance_mode`, `status` (`RecommendationStatus`), `trust_evaluation_ref`, `clamped`/`clamped_from` |
| `AuditSample` (v1.1) | A decision pulled for post-hoc human review at the rung-scaled rate (ADR-0009): `sample_id`, `decision_id`, `agent_id`, `sampled_at`, `reviewed_at`, `reviewer`, `verdict` (`ReviewVerdict`), `reviewer_action`, plus computed `is_reviewed`/`is_pending` |

`DecisionRecord.ground_truth` is documented (in `Action`'s own docstring) as
existing because "every synthetic invoice carries a deterministic correct
answer" — i.e. this field is simulator-sourced by design. How (or whether) the
pipeline is meant to generalize to real, non-synthetic invoices — where ground
truth isn't known at decision time — is an open question, not yet decided.

## The demo script (proposed — not yet buildable)

None of the wiring below exists in code today (see Current Status). This is
the intended shape of a demo once it does:

1. Start an agent at the autonomy floor (₹500).
2. Run the simulator against a batch of synthetic invoices; show the agent
   deciding within its limit.
3. Show the trust score climbing as evidence accumulates, with the Wilson
   lower bound (not the raw accuracy) driving the number — a perfect 10/10
   should visibly *not* be treated as certainty.
4. Show the system recommend an autonomy increase, with the reason codes that
   justify it, and require a human click to authorize it.
5. Inject a critical error (an APPROVE that should have been a REJECT) and
   show the automatic clawback to the floor, with no human step required.
6. Inject a subtler, sustained accuracy drop (not a single critical error) and
   show drift detection catch it — first as a WARNING tripwire, then
   CONFIRMED once the two-proportion z-test has enough samples to back it.
7. Walk through the audit trail: every recommendation and every autonomy
   change should be explainable via its `reason_codes`, not just "the number
   went up."

## Explicit non-goals

- No real bank/ERP/payment integration — everything runs against the
  simulator's synthetic invoices.
- No production-grade auth beyond a JWT/RBAC scaffold — this is a capstone
  prototype, not a hardened multi-tenant system.
- No general-purpose document understanding — invoice "correctness" is a
  deterministic label the simulator assigns, not something the LLM is
  validated against independently.
- No multi-tenant support, no high-availability/scale target — single agent,
  single demo environment.
- No claim that this generalizes beyond invoice approval without further
  design work (see the `ground_truth` open question above).

## Current status

Reality as of **2026-08-23**, not aspiration. Full detail in
`docs/audits/2026-08-23-state-audit.md` (and, for the simulator/frontend row
specifically, `docs/audits/2026-08-23-port-feasibility.md`); this table is
the summary.

| Lane | What exists on `main` | What's stubbed | What's absent |
|---|---|---|---|
| `shared/` (treaty files) | **Merged 2026-08-21, frozen v1.1.** All four files: enums (incl. `RecommendationStatus`, `OpinionVerdict`, `ReviewVerdict`), constants (incl. `SAMPLING_RATE_BY_RUNG`), 18 reason codes, contracts (`DecisionRecord`, `ProportionResult`, `ScoreComponent`, `AgentContext`, `DriftResult`, `TrustEvaluation`, `AgentOpinion`, `Recommendation`, `AuditSample`) | — | Nothing — this is the one lane that's actually done |
| Trust Engine (`trust/`) | Wilson score interval, accuracy/utilization/human-agreement proportions, error breakdown, two-stage drift detection, trust-score composition with weight renormalisation — all pure functions, 113 tests (112 passing, 1 skipped for an optional dev dependency, on CI) | — | Autonomy ladder, cooldowns, and clawback logic (constants exist, e.g. `MIN_SAMPLE_FOR_INCREASE`, `COOLDOWN_BETWEEN_INCREASES`, but nothing implements them yet — due 26 Aug, on schedule); no function produces the actual `TrustEvaluation` contract type — `compute_trust_score()` still returns a different, local `ScoreResult` shape; precision/recall metrics named in the original ownership brief don't exist as functions (only `accuracy()` does) |
| Backend (`backend/`) | Empty directory skeleton (`app/api`, `app/models`, `app/policy`, `app/services`, `app/tasks`, `app/observability`, all `__init__.py`-only) | — | Everything. Zero commits since the 17 Aug scaffold. Its 23 Aug deliverable (`backend/openapi.json`) was missed — rescheduled to 25 Aug |
| Governance (`governance/`) | **Updated 2026-08-29.** On `main` via PRs #6 and #12: the LangGraph workflow (four agent nodes in one parallel superstep, a coordinator, `recommend()` as the whole public surface) and the prompt layer (versioned prompt files per agent, a deterministic evidence renderer, a Pydantic + Gemini-dialect schema boundary validating every model response). On `vc/gemini-client` (PR #15 open): the Gemini HTTP client, an on-disk recording store, and **working `cached` mode** — a recorded response is looked up by `(agent, prompt version, evidence hash)`, validated through the same parser a live response would face, and aggregated into a `Recommendation`. 160 tests, ruff clean, none touching the network | `live` mode raises `NotImplementedError` naming its due date rather than silently serving stub opinions. `governance/recordings/` is empty — recording needs a `GEMINI_API_KEY` and is a deliberate act (`python -m governance.record`), not something that happens on first run | Recording the five demo scenarios (due 30 Aug — the code is built, the recordings are not made); live mode with timeout/retry/fallback (due 3 Sept) |
| Simulator (`simulator/` on `main`) | Empty on `main`. **~5,900 lines of real, working code exist on `origin/ad/simulator-frontend`** (97 tests green there), built against an independently-designed `shared/` incompatible with the frozen one above | — | A merge — the branch conflicts on 5 files and needs porting, not merging, per ADR-0010. Port in progress, due 27 Aug |
| Frontend (`frontend/` on `main`) | Empty on `main`. Same branch as above has 5 working routes, a build that passes `tsc`/`npm run build`, and a chart (`AutonomyTimeline.tsx`) close to reusable as-is — but hand-written types, no `shadcn/ui`, and a leftover scaffold folder (`nexttemp/`) that breaks typecheck until removed | — | A merge, for the same reason as simulator. Frontend type/scaffold cleanup due 29 Aug |

**Bottom line:** the statistical core is real and well-tested. The actual
"earned autonomy" ladder mechanics are still unstarted but on schedule. The
big change since 21 Aug isn't that more is *merged* — `main` itself has not
moved — it's that a large, real, but incompatible body of simulator/frontend
work now exists and needs porting rather than that lane starting from nothing.
See `docs/RISKS.md` and `docs/DEADLINES.md` for what that means for the 15
September deadline.

> **A note on this table's dates.** The non-Governance rows were verified
> against the repo on 2026-08-23 and describe a `main` that has since moved:
> PRs #6–#11 merged the trust ladder and `evaluate()`, the simulator/frontend
> port, and the backend OpenAPI contract, so the Trust, Backend, Simulator and
> Frontend rows above all understate what now exists. Read
> `docs/audits/2026-08-27-delta-audit.md` for the current picture. The
> Governance row was re-verified by its owner on 2026-08-29 and is accurate as
> of then; the paragraph above it still describes the 23 Aug state and is left
> for its owner to revise.
