"""Wilson score interval. Pure: numbers in, numbers out.

Derivation, so you can reproduce it on a whiteboard
---------------------------------------------------
Wald inverts a test whose standard error is estimated from the observed p-hat:

    |p_hat - p| / sqrt(p_hat(1-p_hat)/n)  <=  z

At p_hat = 1 that denominator is zero, so the interval collapses to a point and claims
certainty from ten observations.

Wilson inverts the SCORE test, whose standard error uses the hypothesised p instead:

    |p_hat - p| / sqrt(p(1-p)/n)  <=  z

Square both sides and collect terms in p. The result is a quadratic

    (1 + z^2/n) p^2  -  (2 p_hat + z^2/n) p  +  p_hat^2  =  0

whose two roots are the interval endpoints:

    center = (p_hat + z^2/2n) / (1 + z^2/n)
    margin = z/(1 + z^2/n) * sqrt( p_hat(1-p_hat)/n + z^2/4n^2 )

The z^2/4n^2 term inside the radical never vanishes, which is precisely why the interval
stays non-degenerate at p_hat = 0 and p_hat = 1.

Reference: Brown, Cai & DasGupta (2001), "Interval Estimation for a Binomial Proportion",
Statistical Science 16(2) — the paper documenting Wald's erratic coverage and
recommending Wilson.
"""

from __future__ import annotations

import math

from trust_engine.constants import Z_95


def wilson_interval(successes: int, trials: int, z: float = Z_95) -> tuple[float, float]:
    """Return (lower, upper) for a binomial proportion.

    Edge cases, all deliberate:
      * trials == 0     -> (0.0, 1.0). No evidence means maximal uncertainty.
      * successes == 0  -> lower is exactly 0.0.
      * successes == trials -> upper is exactly 1.0, lower is strictly below 1.0.
        This is the case the whole module exists for.
    """
    if trials < 0 or successes < 0:
        raise ValueError("counts must be non-negative")
    if successes > trials:
        raise ValueError(f"successes ({successes}) cannot exceed trials ({trials})")
    if trials == 0:
        return 0.0, 1.0

    n = float(trials)
    p_hat = successes / n
    z2 = z * z

    denominator = 1.0 + z2 / n
    center = (p_hat + z2 / (2.0 * n)) / denominator
    radicand = (p_hat * (1.0 - p_hat)) / n + z2 / (4.0 * n * n)
    margin = (z * math.sqrt(max(radicand, 0.0))) / denominator

    lower = _clamp01(center - margin)
    upper = _clamp01(center + margin)

    # Snap the degenerate endpoints. Floating point leaves the k=0 lower bound at ~7e-18
    # rather than 0 — harmless arithmetically, but it makes audit output and assertions
    # lie about what the evidence says.
    if successes == 0:
        lower = 0.0
    if successes == trials:
        upper = 1.0

    return lower, upper


def wilson_lower_bound(successes: int, trials: int, z: float = Z_95) -> float:
    """The conservative claim: the worst true rate consistent with the evidence.

    Used one-sided, the lower endpoint of a two-sided 95% interval is a 97.5% confidence
    statement. Say so before a judge does.
    """
    return wilson_interval(successes, trials, z)[0]


def _clamp01(x: float) -> float:
    if math.isnan(x):
        return 0.0
    return 0.0 if x < 0.0 else (min(x, 1.0))