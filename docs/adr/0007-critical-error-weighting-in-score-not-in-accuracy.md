# ADR-0007: Critical-error weighting lives in the trust score, not in the accuracy proportion

## Status

Accepted

## Context

Not all wrong decisions are equally bad. Approving an invoice that should have
been rejected sends money out the door; rejecting one that should have been
approved is friction, not loss. `shared/constants.py`'s
`CRITICAL_ERROR_DEFINITION` states this directly: "The agent APPROVED an
invoice whose ground truth is REJECT. Money leaves the building. Rejecting a
valid invoice is an error but NOT a critical one." The trust engine needs to
reflect that asymmetry somewhere — the question is *where*.

## Decision

The severity weighting (`CRITICAL_ERROR_WEIGHT=5.0`,
`trust/trust_engine/constants.py:35`) is applied **only** inside the
critical-error penalty component of the trust score
(`critical_error_penalty()`, `trust/trust_engine/score.py:60-66`), and
explicitly **not** inside the accuracy proportion itself. `accuracy()`
(`trust/trust_engine/stats/rates.py:62-68`) counts a critical error and a
non-critical error identically — both just reduce `correct/acted` by one.

The module docstring states the reason directly:
`trust/trust_engine/score.py:23-25` — "The 5x weight applies HERE, and
nowhere else — never inside the accuracy proportion, which would invalidate
the Wilson bound derived from it."

## Consequences

- The Wilson interval (ADR-0002) is a bound on a true binomial proportion. Its
  correctness depends on every trial being a plain 0/1 outcome — introducing a
  5x-weighted "trial" would no longer be a binomial proportion at all, and the
  Wilson formula's guarantees would no longer apply. Keeping severity
  weighting entirely out of `accuracy()` is what keeps that math valid.
- This is directly tested: `trust/tests/test_score.py` (`test_weighting_lives_outside_the_accuracy_proportion`)
  asserts that `accuracy()`'s Wilson lower bound is identical whether ten
  errors in a 100-decision sample are critical or non-critical — the
  proportion literally cannot see the distinction; only the score can.
- The penalty is a separate, capped component:
  `1.0 − CRITICAL_ERROR_WEIGHT × (critical_errors / acted_total)`, clamped to
  `≥ 0.0` (`score.py:63-66`) — a clean 20% critical-error rate zeroes the
  component out entirely (`5.0 × 0.20 = 1.0`), tested exactly at that
  boundary (`test_penalty_reaches_zero_at_the_weighted_rate`).
- `critical_error_penalty()` returns `None`, not `0.0`, when there are no
  acted decisions at all (`score.py:64-65`) — "undecided" is deliberately not
  scored the same as "clean," which matters because the score composition
  drops components with no evidence rather than penalizing their absence at
  face value (a fixed regression — see `test_agent_that_escalates_everything_scores_near_zero`
  in `trust/tests/test_score.py`, guarding against an earlier version that
  scored "escalate everything, decide nothing" at 68.8/100).
- Cost: this means "how bad is this agent's accuracy, really" requires
  reading two numbers together (the Wilson-bound accuracy *and* the critical
  penalty component) rather than one composite figure — by design, since
  collapsing them into a single weighted accuracy would be exactly the thing
  this ADR rejects.

## Alternatives considered

- **Weight critical errors directly inside the accuracy proportion** (e.g.
  count a critical error as 5 failures instead of 1). Rejected: breaks the
  Wilson interval's statistical validity, as above — the interval would no
  longer correspond to any real confidence level.
- **Two entirely separate accuracy metrics** (critical-only accuracy,
  non-critical-only accuracy) instead of one accuracy plus one penalty
  component. Rejected as unnecessarily fragmenting the trust score into more
  independent numbers than the four-component weighting scheme
  (`WEIGHT_WILSON_LOWER`, `WEIGHT_HUMAN_AGREEMENT`, `WEIGHT_CRITICAL_PENALTY`,
  `WEIGHT_UTILIZATION`, `score.py:17-20`) was designed to compose — the
  penalty-component approach keeps exactly one place (`WEIGHT_CRITICAL_PENALTY=0.15`)
  where "how much should critical errors matter to the final score" is tuned.
- **A hard cutoff** (any critical error immediately zeroes the trust score).
  Rejected as the trust-score-level version of the same mistake ADR-0006
  guards against for drift: a single critical error already forces an
  unconditional drift `CRITICAL` severity and clawback path
  (`trust/trust_engine/stats/drift.py:110-115`) — using the *score* itself as
  a second all-or-nothing switch for the same event would be redundant and
  would remove the score's ability to express "mostly good, one serious
  mistake" as a number rather than a cliff.
