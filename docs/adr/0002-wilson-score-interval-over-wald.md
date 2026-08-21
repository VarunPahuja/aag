# ADR-0002: Wilson score interval over the Wald (normal-approximation) interval

## Status

Accepted

## Context

Every proportion the trust engine reports — accuracy, human agreement,
utilization — is a success count over a trial count, and small-sample
proportions lie. An agent that has approved 10/10 invoices correctly and one
that has approved 500/500 correctly both report 100% accuracy, but they don't
deserve the same trust. The engine needs a confidence interval around each
proportion, not just the raw rate, and needs one that behaves correctly at the
extremes (`p̂ = 0` or `p̂ = 1`), which is exactly where a small, recently-active
agent will usually sit.

## Decision

Use the **Wilson score interval**, not the Wald (normal-approximation)
interval, for every proportion, and drive gating decisions off its **lower
bound**, not the point estimate.

Implemented in `trust/trust_engine/stats/wilson.py:40-77`. The module's own
docstring derives it from inverting the score test
(`|p̂−p| / sqrt(p(1−p)/n) ≤ z`) rather than the Wald test
(`|p̂−p| / sqrt(p̂(1−p̂)/n) ≤ z`) — the distinction matters because the Wald
denominator is estimated from the *observed* `p̂`, which is exactly zero at
`p̂ = 1`, collapsing the interval to a single point and claiming certainty from
as few as one sample.

## Consequences

- `wilson_lower_bound(10, 10)` ≈ 0.7225 while `wilson_lower_bound(500, 500)` ≈
  0.9923 (`trust/tests/test_wilson.py:240-246`) — a perfect small sample is
  visibly *not* treated as proof, which is the entire point of gating on the
  lower bound rather than the raw rate.
- At `successes == trials`, the upper bound is forced to exactly `1.0` while
  the lower bound stays strictly below it (`wilson.py:73-75`) — this is, per
  the module's own comment, "the case the whole module exists for."
  `successes == 0` similarly forces the lower bound to exactly `0.0`
  (`wilson.py:71-72`), correcting float noise that would otherwise leave it at
  ~7e-18.
- `trials == 0` returns `(0.0, 1.0)` — maximal uncertainty, not a division
  error (`wilson.py:53-54`).
- The z-value is `Z_95 = 1.96` (`trust/trust_engine/constants.py:14`), the
  conventional rounded 95% value rather than the exact `1.959963984540054`
  (immaterial difference, ~4e-5). It is a keyword parameter on both
  `wilson_interval` and `wilson_lower_bound`, so a caller can override the
  z-score per call, but there is no "confidence level as a percentage"
  parameter — the caller has to already know the z-score for whatever level
  they want.
- The implementation is cross-validated against an independent reference
  (`statsmodels.stats.proportion.proportion_confint(method="wilson")`) in
  `trust/tests/test_wilson.py:334-343`, not just self-consistency tests.
- Cost: the formula is less immediately readable than the Wald interval (the
  module docstring spends 20 lines deriving it), and every caller has to
  remember to read `wilson_lower`, not `point`, when gating a decision —
  nothing in the type system stops a future caller from reading
  `ProportionResult.point` instead and silently losing the small-sample
  correction.

## Alternatives considered

- **Wald / normal-approximation interval.** Rejected: collapses to zero width
  at `p̂ ∈ {0, 1}`, which is precisely the region a new or recently-clawed-back
  agent lives in — the interval that's supposed to express uncertainty would
  claim none, exactly when there's the most.
- **Raw point estimate with a fixed minimum sample size gate.** Rejected: a
  hard sample-size cutoff is a blunt instrument — it can't express "80% sure
  vs. 99% sure," only "enough samples or not," and doesn't degrade gracefully
  as an agent accumulates more evidence past the cutoff.
- **Clopper-Pearson (exact) interval.** Not chosen: notoriously conservative
  (wider than necessary) especially at small `n`, which would make it harder
  for a genuinely good agent to ever clear a trust threshold. Wilson is the
  standard middle ground recommended by Brown, Cai & DasGupta (2001), cited
  directly in the module docstring.
