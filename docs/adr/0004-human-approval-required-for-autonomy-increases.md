# ADR-0004: Autonomy increases require human authorization; clawbacks do not

## Status

Accepted (contract-level; enforcement not yet implemented — see Consequences)

## Context

The system can recommend two very different kinds of change to an agent's
autonomy: give it *more* authority, or take authority *away*. These are not
symmetric risks. Granting more spending authority to an agent that turns out
not to deserve it is the exact failure mode the entire project exists to
prevent. Reducing an agent's authority when its performance has degraded is
the safe direction to fail in — the cost of an unnecessary clawback is
friction, not money out the door.

## Decision

**Increasing** an agent's autonomy limit requires a human to authorize the
system's recommendation before it takes effect. **Reducing** it (clawback,
whether from confirmed drift or a critical error) is applied automatically,
with no human step required.

This is visible in the contract shape itself, not just in prose: `shared/contracts.py`'s
`TrustEvaluation` has `recommended_limit` / `recommended_rung` — a
*recommendation*, not an `applied_limit` — plus a separate boolean
`eligible_for_increase`. Nothing in the contract has an equivalent
"recommended clawback, pending approval" shape; `DriftSeverity.CRITICAL`
(`shared/enums.py`) is designed as an immediate, unconditional signal — the
drift detector's own short-circuit logic (`trust/trust_engine/stats/drift.py:110-115`)
returns `CRITICAL` the instant a critical error is found in the recent window,
skipping the statistical tripwire/z-test path entirely that a milder drift
signal has to pass through. There is no equivalent "skip the checks and
apply immediately" path anywhere for an *increase*.

## Consequences

- An increase can be wrong and caught before it costs anything — a human sees
  the reason codes and the evidence and can decline it.
- A clawback can never be delayed by an unavailable reviewer — the system's
  most safety-critical action doesn't wait on a person.
- This means the "recommendation" produced by governance
  (`vc/governance`, `Direction.INCREASE`) is inert on its own — it is data
  for a human decision, not an instruction the Policy Engine executes
  unattended. The UI/API surface for that human decision point doesn't exist
  yet (no code in `vp/backend` or `ad/simulator-frontend` as of 2026-08-21).
- **Honesty check:** the *contract* supports this asymmetry, but the
  *enforcement* of it does not exist yet — the autonomy-ladder/cooldown logic
  that would even produce a `recommended_limit` in the first place is
  unimplemented in `trust/trust_engine/` (only its constants exist:
  `MIN_SAMPLE_FOR_INCREASE`, `MIN_TRUST_SCORE_FOR_INCREASE`,
  `COOLDOWN_BETWEEN_INCREASES` in `trust/trust_engine/constants.py:27-28,43`).
  This ADR records the decision so it's built correctly the first time, not a
  claim that it's already enforced.

## Alternatives considered

- **Fully automatic increases**, mirroring the automatic clawback. Rejected:
  removes the one deliberate friction point in a system whose entire premise
  is that autonomy should be *earned* under scrutiny, not compounding on its
  own once a threshold is crossed — and it collapses the LLM-reasons /
  humans-authorize split from ADR-0001 into "LLM reasons and that's
  sufficient," which is the thing this architecture is built to avoid.
- **Human approval for both directions.** Rejected: gating clawback behind
  human availability turns the one thing the system is supposed to do
  reliably — respond fast to degrading performance — into something that can
  stall exactly when it matters most.
- **Automatic increases with a fast-follow human audit** (act first, review
  after). Rejected: for a system whose stated goal is defensibility "before a
  judge," being able to say "a human approved this before it happened" is
  worth more than being able to say "a human reviewed it afterward."
