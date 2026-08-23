# Trust Lane — AI Context Primer

**Paste this whole file into your AI assistant at the start of a session. It has
everything needed to work on this lane with no other context.**

---

## The project

We are four final-year students building a capstone prototype for Deloitte
USI, due **15 September 2026**. It is called the **Adaptive AI Governance
Platform (Earned Autonomy Engine)**.

The problem: an AI agent that processes invoices should not be handed unlimited
authority on day one. It starts with a small autonomy limit (it may approve
invoices up to ₹500 by itself, anything larger must be escalated to a human).
As it demonstrates reliable performance, backed by enough statistical evidence,
the system can recommend raising that limit to ₹1,000, ₹2,500, ₹5,000, ₹10,000.
A human must approve every increase. If performance degrades, the system detects
it and claws the limit back automatically, no human needed.

The single design rule the whole architecture is built on:

> **LLM reasons. Statistics provide evidence. Policy Engine enforces. Humans
> authorize.**

The LLM never changes a permission. It writes explanations and recommendations.
The statistics say what the evidence is. A deterministic policy engine is the
only thing that enforces a limit. A human signs off on every increase.

## Who owns what

Four lanes, four owners, one monorepo:

| Lane | Owner | Directory |
|---|---|---|
| Backend & Policy | Varun P. (team lead) | `backend/` |
| **Trust & Risk (this lane)** | **Utkarsh** | **`trust/`** |
| Agentic Governance | Varun C. | `governance/` |
| Simulator | Adhya (port), **then you** | `simulator/` |
| Frontend | Adhya | `frontend/` |

`shared/` holds the cross-lane contracts and belongs to all four. It is frozen
until 9 September. Do not modify anything in `shared/` — if a change is needed,
stop and raise it with the whole team.

You are also **backup reviewer** as of 23 Aug: if VP is unavailable (he has
interview commitments 24 Aug - 3 Sept), you can approve and merge anything
that doesn't touch `shared/` — that still needs all four. See
`docs/DEADLINES.md`.

---

## This lane's job

The trust engine is a **pure statistical library**. It takes a list of decisions
an agent has made and returns an evidence-based evaluation: how accurate has it
been, how confident are we given the sample size, is it degrading, and what
autonomy limit does the evidence support.

### Hard boundaries — do not violate these

- No FastAPI, no web framework, no HTTP.
- No database access of any kind (no SQLAlchemy, psycopg, ORM, raw SQL).
- No Redis, no Celery, no message queues.
- No network calls (no `requests`, no `httpx`).
- No file I/O.
- No reading the wall clock (`datetime.now()`, `time.time()`). Timestamps come
  in as arguments.
- No global mutable state.
- Pure functions wherever possible: same inputs, same outputs, no side effects.

The reason for these rules is not style. The trust engine is the evidence layer
of a governance system. It has to be independently testable and deterministically
reproducible, because a judge will ask "how do I know this number is right." The
answer is "run the function with these inputs, you get this output, every time."

If your AI suggests adding a database call or an API endpoint to this lane, it
has misunderstood the architecture. Refuse it.

---

## What already exists (done, tested, do not rewrite)

`trust/trust_engine/` currently contains ~470 lines of engine code and ~1,000
lines of tests. 112 tests pass, 1 skips. This work is audited and correct.

| Module | Contents |
|---|---|
| `stats/wilson.py` | `wilson_interval(successes, trials, z)`, `wilson_lower_bound(...)`. Wilson score interval, not Wald. Handles n=0, k=0, k=n, impossible counts. Cross-validated against `statsmodels`. |
| `stats/rates.py` | `partition()`, `accuracy()`, `utilization()`, `human_agreement()`, `error_breakdown()`. All return `ProportionResult` from `shared/`. |
| `stats/drift.py` | `split_history()`, `two_proportion_z()`, `critical_errors_in_window()`, `detect_drift()`. Two-stage: an accuracy-drop tripwire, then a pooled two-proportion z-test to confirm. Returns `DriftResult`. |
| `score.py` | `critical_error_penalty()`, `compute_trust_score()`. Weighted composition with renormalisation when a component lacks evidence. |
| `constants.py` | Lane-local tunables. |

Lane-local constants in `trust/trust_engine/constants.py`:

```
Z_95 = 1.96
WEIGHT_WILSON_LOWER = 0.50
WEIGHT_HUMAN_AGREEMENT = 0.25
WEIGHT_CRITICAL_PENALTY = 0.15
WEIGHT_UTILIZATION = 0.10
CRITICAL_ERROR_WEIGHT = 5.0
MIN_RULED_ESCALATIONS_FOR_AGREEMENT = 5
RECENT_WINDOW = 50
CRITICAL_ERROR_WINDOW = 20
DRIFT_ACCURACY_DROP_PP = 10.0
DRIFT_MIN_N_FOR_TEST = 30
DRIFT_ALPHA = 0.05
MIN_SAMPLE_FOR_INCREASE = 30
MIN_TRUST_SCORE_FOR_INCREASE = 70.0
COOLDOWN_BETWEEN_INCREASES = 100
CLEAN_DECISIONS_AFTER_CLAWBACK = 75
```

The last four are currently **dead** — defined but nothing reads them. That is
this lane's remaining work.

## The shared contracts you consume and produce

From `shared/contracts.py` (frozen dataclasses):

- `DecisionRecord` — one decision the agent made. Fields: `decision_id`,
  `sequence`, `invoice_id`, `amount`, `action`, `ground_truth`, `agent_id`,
  `decided_at`, `recommended_action`, `human_ruling`. Computed properties:
  `is_escalated`, `is_acted`, `is_correct`, `is_critical_error`,
  `is_noncritical_error`, `has_human_ruling`, `human_agreed`.
- `ProportionResult` — `successes`, `trials`, `point`, `wilson_lower`,
  `wilson_upper`, `has_evidence`.
- `ScoreComponent` — `name`, `value`, `nominal_weight`, `effective_weight`,
  `available`, `contribution`.
- `AgentContext` — **input you need and currently ignore.** `current_limit`,
  `decisions_since_last_change`, `decisions_since_clawback`, `state`.
- `DriftResult` — severity, detected, accuracies, drop_pp, z, p, window sizes,
  underpowered flag.
- `TrustEvaluation` — **the output contract. Nothing currently produces it.**

From `shared/enums.py`: `Action` (APPROVE/REJECT/ESCALATE), `AgentState`
(probation/active/restricted/suspended), `DriftSeverity`
(NONE/WARNING/CONFIRMED/CRITICAL), `Direction` (INCREASE/HOLD/CLAWBACK).

From `shared/constants.py`: `AUTONOMY_LADDER = (500, 1000, 2500, 5000, 10000)`,
`AUTONOMY_FLOOR = 500`, `MAX_RUNG = 4`, `rung_of(limit)`, `limit_of(rung)`.

From `shared/reason_codes.py`: 15 string constants. Only 3 are currently
emitted. The other 12 all belong to the work below.

---

## Deliverables

### Due 26 August — `uk/autonomy-ladder`, branched off `main`

Build the orchestrator and the autonomy decision logic. This is the part that
makes the project an *earned autonomy* engine rather than a statistics library.
Everything else in the system waits on it.

**1. The orchestrator.**

```python
def evaluate(
    decisions: Sequence[DecisionRecord],
    context: AgentContext,
) -> TrustEvaluation:
    ...
```

One call. It runs `accuracy`, `utilization`, `human_agreement`,
`error_breakdown`, `detect_drift`, `compute_trust_score`, then applies the
ladder logic below, and assembles the complete `TrustEvaluation`. Every field
of the contract must be populated. This is the only function the backend will
call.

**2. Retire the local `ScoreResult`.** `compute_trust_score()` currently returns
a lane-local dataclass that is a second, incompatible shape for the same idea.
Feed it into the orchestrator and let `TrustEvaluation` be the only public
result type. Note the field rename: `renormalised` becomes
`weights_renormalised`.

**3. The autonomy ladder.** Given a trust score and an `AgentContext`, decide
`direction`, `recommended_rung`, `recommended_limit`, and `eligible_for_increase`.

An **increase** requires all of:
- acted decisions >= `MIN_SAMPLE_FOR_INCREASE` (else `INSUFFICIENT_SAMPLE`)
- trust score >= `MIN_TRUST_SCORE_FOR_INCREASE` (else `TRUST_BELOW_THRESHOLD`)
- `decisions_since_last_change` >= `COOLDOWN_BETWEEN_INCREASES` (else `COOLDOWN_ACTIVE`)
- not already at `MAX_RUNG` (else `AT_MAX_RUNG`)
- no active drift (else `DRIFT_ACTIVE`)
- if there was a prior clawback, `decisions_since_clawback` >=
  `CLEAN_DECISIONS_AFTER_CLAWBACK` (else `CLAWBACK_RECOVERY_PENDING`)

When all pass, emit `EVIDENCE_SUFFICIENT`, `NO_DRIFT_DETECTED`,
`NO_RECENT_CRITICAL_ERRORS`, `COOLDOWN_SATISFIED` as applicable.

A **clawback** fires when drift severity is CONFIRMED or CRITICAL
(`CLAWBACK_DRIFT`), or a critical error appears in the recent window
(`CLAWBACK_CRITICAL_ERROR`). Clawback drops exactly one rung, never below
`AUTONOMY_FLOOR`.

Increases move exactly one rung at a time. Never skip rungs, even with
overwhelming evidence — an increase is a human-authorized event and jumping two
rungs on one approval defeats the point.

**4. All 18 reason codes must be reachable**, each with a test that produces it.
The reason codes are how the dashboard and the audit log explain *why* a
decision went the way it did. An unreachable code is a lie in the contract.

**5. Keep `current_limit` and `current_rung` consistent.** The contract stores
both. Assert `rung_of(current_limit) == current_rung` inside `evaluate` and fail
loudly if a caller passes an inconsistent `AgentContext`.

**6. Tests, to the standard already set in this lane.** Real numeric assertions,
boundary cases, and at least one test per reason code. Property tests where they
fit.

### Fri 4 September — simulator finalised, branched off `main`

This is no longer a from-scratch build. Adhya already built a working
simulator — invoice generator, degradation phases, cache, CLI — the problem
was it was built against her own version of `shared/`, not `main`'s. She
ports it onto the real contracts between 24 and 27 Aug
(`docs/audits/2026-08-23-port-feasibility.md` has the file-by-file detail).
You take it over once it's ported, because she can't finish the port and
build the entire dashboard in the time left — not because the simulator work
itself was wasted.

By the time it lands in your hands it should already have:
- Invoice generator: amount distribution spanning the ladder rungs, vendor,
  category, timestamp, and a deterministic correct `Action` — ported from her
  category-tier logic onto the 5-rung ladder, not rebuilt
- A "good performance" phase, a "degraded" phase with injected errors
  (including critical ones, so drift detection fires), and a recovery phase
- Seeded and deterministic generation
- The duplicate `wilson_lower_bound` her `runner.py` reimplemented deleted,
  replaced by importing `trust/trust_engine/stats/wilson.py`'s version —
  exactly one implementation of it should exist in this repo after this lands

Your job Thu 27 Aug - 4 Sept: verify the port actually holds up under real
use, finalise the phase tuning against the ladder (not the tier table), and
commit fixtures so the demo can replay without generating live. The whole
ten-beat demo has to be reproducible from one command. If the simulation is
non-deterministic, the demo is a gamble.

Not ported, cut outright: `simulator/simulator/agents/llm.py`, the agent that
called Gemini directly from inside the simulator. That's the simulator making
LLM calls outside `vc/governance`'s lane — a real boundary violation of
ADR-0001, not a stylistic one. The scripted agent and cached-mode agent cover
what the demo needs.

---

## How to work

- Branch off `main`, not off `uk/trust` (it's already merged, don't extend it).
- Feature branches live two days maximum. If it's bigger, split it.
- PR into `main`. CI must pass. No direct pushes.
- One line in `docs/DECISION_LOG.md` per merged PR.
- Any architectural decision gets an ADR in `docs/adr/` **before** the code
  lands, not as after-the-fact justification. Read the existing ADRs 0001-0008
  first, particularly 0002 (Wilson over Wald), 0006 (two-stage drift), and 0007
  (critical error weighting) — those describe your lane.
- Daily standup message by 11:00: done / doing / blocked.

## Escalate, don't decide alone

Raise these with Varun P. rather than choosing yourself:

- Anything that would need a change in `shared/`.
- Changing a constant that affects the demo narrative (window sizes, thresholds,
  weights). The demo has to show an increase and a clawback within a few hundred
  simulated invoices, so these numbers are demo-tuned, not just statistically
  motivated.
- Anything that would make `evaluate()` non-deterministic.

## Instructions for the AI assistant reading this

- Explain the statistics, don't just emit code. This is a capstone; the human
  has to defend every formula to a technical panel.
- Do not write code outside `trust/`.
- Do not modify `shared/`.
- Do not add dependencies without asking. This lane currently needs nothing
  beyond the standard library; `numpy` and `scipy` were deliberately removed.
- When suggesting a statistical method, state its standard name, and say
  explicitly when you are deviating from the textbook form and why.
- Prefer pure functions. If you find yourself wanting state, say so and explain
  the alternative rather than silently introducing it.