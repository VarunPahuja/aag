# CONTEXT.md — Adaptive AI Governance Platform (AAGP)

This is the single source of truth for the project. If you are new to the repo — a
teammate, a mentor, a judge — start here. It is written to require zero prior
context. Everything in this file is checked against the actual repo state as of
**2026-08-21**; where the code doesn't yet match the intent, that's stated
explicitly rather than glossed over.

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

| Lane | Branch | Owns |
|---|---|---|
| Backend | `vp/backend` | FastAPI, Postgres, SQLAlchemy, Alembic, the Policy Engine, API endpoints, JWT/RBAC, Docker Compose, and wiring the other three lanes together |
| Trust Engine | `uk/trust` | Wilson confidence bounds, accuracy/human-agreement metrics, critical-error weighting, recent-vs-historical drift detection, trust score composition, the autonomy ladder, cooldowns, and tests. **Hard rules**: no FastAPI, no SQLAlchemy/psycopg/DB access, no Redis, no Celery, no network calls. Pure functions wherever possible. Must emit the `TrustEvaluation` contract. |
| Governance | `vc/governance` | LangGraph governance agents, Gemini integration, human-readable recommendations |
| Simulator + Dashboard | `ad/simulator-frontend` | Synthetic invoice generation (with deterministic ground truth) and the Next.js dashboard |

Cross-lane contracts — the types every lane agrees to use — live in `shared/`
and are governed as a "treaty": see
[ADR-0005](adr/0005-shared-contracts-as-cross-lane-treaty.md) and
`CONTRIBUTING.md`.

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

### `shared/constants.py`

`SCHEMA_VERSION="1.0"`, `CURRENCY="INR"`, `AUTONOMY_LADDER=(500, 1000, 2500,
5000, 10000)`, `AUTONOMY_FLOOR=500`, `MAX_RUNG=4`, `TRUST_SCORE_MIN/MAX=0.0/100.0`,
`CRITICAL_ERROR_DEFINITION` (a critical error is APPROVE-ing an invoice whose
ground truth is REJECT — money leaves the building; the reverse is an error but
not a critical one), plus `rung_of(limit)` / `limit_of(rung)` helpers.

### `shared/reason_codes.py`

15 machine-readable string constants (increase-blocked reasons, increase-allowed
reasons, clawback reasons, evidence-quality notes) plus a `HUMAN_READABLE` dict
and a `describe(codes)` formatter — the rule is the human-readable sentence is
always generated *from* a code, never written free-hand.

### `shared/contracts.py`

| Type | Fields |
|---|---|
| `DecisionRecord` | `decision_id`, `sequence`, `invoice_id`, `amount`, `action`, `ground_truth`, `agent_id="agent-01"`, `decided_at=None`, `recommended_action=None`, `human_ruling=None`, plus computed properties `is_escalated` / `is_acted` / `is_correct` / `is_critical_error` / `is_noncritical_error` / `has_human_ruling` / `human_agreed` |
| `ProportionResult` | `successes`, `trials`, `point`, `wilson_lower`, `wilson_upper` |
| `ScoreComponent` | `name`, `value`, `nominal_weight`, `effective_weight`, `available` |
| `AgentContext` | `current_limit=AUTONOMY_FLOOR`, `decisions_since_last_change=0`, `decisions_since_clawback=None`, `state=PROBATION` — the agent's standing, supplied by the backend |
| `DriftResult` | `severity=NONE`, `detected=False`, `recent_accuracy`, `baseline_accuracy`, `drop_pp`, `z_statistic`, `p_value`, `critical_errors_in_window=0`, `recent_n=0`, `baseline_n=0`, `underpowered=False` |
| `TrustEvaluation` | The complete engine output: identity/versioning, decision counts, the three `ProportionResult`s, error counts, `trust_score` + `components` + `weights_renormalised`, `drift`, ladder position (`current_limit/rung`, `recommended_limit/rung`, `direction`, `eligible_for_increase`), `state`, `reason_codes`, `evaluated_at`, `config_fingerprint` |

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

Reality as of **2026-08-21**, not aspiration. (`main` itself is still an empty
directory skeleton; the trust engine and shared contracts described here exist
on branches — see `DECISION_LOG.md` for how those branches relate.)

| Lane | What exists | What's stubbed | What's absent |
|---|---|---|---|
| `shared/` (treaty files) | All four files fully defined: enums, constants, reason codes, contracts (`DecisionRecord`, `ProportionResult`, `ScoreComponent`, `AgentContext`, `DriftResult`, `TrustEvaluation`) | — | Not yet merged to `main` |
| Trust Engine (`uk/trust`) | Wilson score interval, accuracy/utilization/human-agreement proportions, error breakdown, two-stage drift detection, trust-score composition with weight renormalisation — all pure functions, 113 tests (112 passing, 1 skipped for an optional dev dependency) | — | Autonomy ladder, cooldowns, and clawback logic (constants exist, e.g. `MIN_SAMPLE_FOR_INCREASE`, `COOLDOWN_BETWEEN_INCREASES`, but nothing implements them); no function produces the actual `TrustEvaluation` contract type — `compute_trust_score()` returns a different, local `ScoreResult` shape instead; precision/recall metrics named in the ownership brief don't exist as functions (only `accuracy()` does) |
| Backend (`vp/backend`) | Empty directory skeleton (`app/api`, `app/models`, `app/policy`, `app/services`, `app/tasks`, `app/observability`, all `__init__.py`-only) | — | Everything: FastAPI app, Postgres/SQLAlchemy models, Alembic migrations, the Policy Engine, API endpoints, JWT/RBAC, Docker Compose content, and any code that calls into the trust engine |
| Governance (`vc/governance`) | Empty directory skeleton (`governance/agents`, `governance/prompts`) | — | Everything: LangGraph agents, Gemini integration, recommendation generation, any `Recommendation`-shaped contract (none exists in `shared/` either) |
| Simulator + Dashboard (`ad/simulator-frontend`) | Empty directory skeleton (`simulator/simulator/agents`, `frontend/src/{app,components,lib,mocks,types}`) | — | Everything: synthetic invoice generation, the governed agent itself, the Next.js dashboard |

**Bottom line:** the statistical core is real and well-tested; the product
around it — the actual "earned autonomy" mechanics, and three of the four
lanes — has not been started. See `docs/RISKS.md` for what that means for the
deadline.
