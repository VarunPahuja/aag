# ADR-0006: Two-stage drift detection — accuracy tripwire, then a z-test

## Status

Accepted

## Context

Lifetime accuracy hides recent degradation: an agent with 400 good decisions
and 50 recent terrible ones still shows roughly 89% overall — nothing about
that number alone would flag a problem. The system needs to compare *recent*
performance against a *historical baseline* to catch a live collapse before it
compounds. But a naive threshold on the recent-vs-baseline gap has an obvious
failure mode of its own: over a modest sample, a swing of several percentage
points can easily be noise, not a real change in the agent's behavior. A pure
significance test has the opposite problem: statistically sound but hard to
explain to a non-statistician (a reviewer, a judge) as "why did the system act
just now."

## Decision

Drift detection is two separate stages, both of which have to agree before a
degradation is treated as confirmed (`trust/trust_engine/stats/drift.py:93-162`):

1. **Tripwire** — `split_history()` (`drift.py:37-51`) splits decisions into
   the last `RECENT_WINDOW=50` (`trust/trust_engine/constants.py:29`) as
   "recent" and everything before as "baseline." If the accuracy drop exceeds
   `DRIFT_ACCURACY_DROP_PP=10.0` percentage points (`drift.py:38-40,132`),
   the tripwire fires and raises severity to at least `WARNING`. Fast, blunt,
   and easy to state in one sentence.
2. **Confirmation** — a two-proportion pooled z-test (`two_proportion_z()`,
   `drift.py:58-79`) checks whether that gap is unlikely to be chance. If both
   the recent and baseline samples clear `DRIFT_MIN_N_FOR_TEST=30`
   (`constants.py:39`) and the one-sided p-value is below `DRIFT_ALPHA=0.05`
   (`constants.py:40`), severity upgrades from `WARNING` to `CONFIRMED`
   (`drift.py:142-150`). If the samples are too small, severity stays
   `WARNING` and the result is flagged `underpowered=True` rather than
   silently claiming statistical confidence it doesn't have.

A single critical error inside the last `CRITICAL_ERROR_WINDOW=20` acted
decisions (`constants.py:30`) short-circuits both stages entirely and forces
`DriftSeverity.CRITICAL` immediately (`drift.py:107-115`) — see ADR-0007 and
ADR-0004 for why that path is deliberately unconditional.

## Consequences

- A single unlucky streak within an otherwise-good history cannot, by itself,
  trigger a clawback-worthy `CONFIRMED` — it has to clear both the blunt
  threshold and the statistical test. Tested directly:
  `trust/tests/test_drift.py` — a 350-good/50-bad split reaches `CONFIRMED`
  only because both `drop_pp > 10.0` *and* `p_value < 0.05` hold; a smaller
  drop below the 10pp tripwire stays `NONE` even though *some* z-test signal
  might exist for it.
- The `underpowered` flag means the system can say "this looks like drift but
  I don't have enough data to be sure yet" instead of forcing a binary
  yes/no — a real, distinct state (`WARNING` + `underpowered=True`) that a
  human reviewer can act on differently than a statistically `CONFIRMED` one.
- Cost: two hardcoded thresholds (`10.0` pp, `30` minimum n) have to be tuned
  together, and a change to one can silently change how often the other
  branch is reached — there's no single "sensitivity" knob, by design (per
  the module's own docstring, this tradeoff is intentional: "the tripwire
  alone would claw back autonomy from an agent that did nothing wrong; the
  z-test alone would be harder to explain to a judge").
- `RECENT_WINDOW=50` decisions means an agent needs at least that many acted
  decisions of history before any baseline comparison is even possible —
  `split_history()` returns an empty baseline and `NONE` severity below that
  (`drift.py:47-51`, tested `trust/tests/test_drift.py`), so a brand-new
  agent cannot be flagged for drift it hasn't had time to exhibit.

## Alternatives considered

- **Tripwire only** (a flat percentage-point drop threshold, no significance
  test). Rejected: a 10pp swing over 50 decisions can plausibly be luck; using
  it alone to trigger an automatic clawback (ADR-0004) risks punishing an
  agent that didn't actually get worse.
- **Statistical test only** (no blunt tripwire, act purely on p-value).
  Rejected: technically sound but produces a result that's hard to defend in
  plain language — "the z-statistic was -2.1" is not an answer a non-technical
  reviewer, or a judge, will find satisfying on its own; pairing it with the
  percentage-point tripwire gives a number anyone can sanity-check
  independently of the statistics.
- **A single continuous drift "score"** instead of a severity tier. Rejected
  for the same reason score renormalisation was kept explicit (ADR-0007):
  collapsing tripwire-fired-but-unconfirmed and statistically-confirmed into
  one number would hide exactly the distinction (noise vs. real signal) the
  two-stage design exists to preserve.
