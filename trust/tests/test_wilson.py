"""Wilson correctness — these tests ARE the statistical-correctness deliverable."""

from __future__ import annotations

import math

import pytest

from trust_engine.constants import Z_95
from trust_engine.stats.wilson import wilson_interval, wilson_lower_bound


@pytest.mark.parametrize(
    "n,expected_lower",
    [(10, 0.7225), (30, 0.8865), (100, 0.9630), (500, 0.9923)],
)
def test_perfect_record_lower_bound_grows_with_sample_size(n, expected_lower):
    """The headline claim: a perfect ten is not proof."""
    assert wilson_lower_bound(n, n) == pytest.approx(expected_lower, abs=1e-4)


def test_naive_accuracy_cannot_distinguish_these_cases():
    assert 10 / 10 == 500 / 500 == 1.0
    assert wilson_lower_bound(10, 10) < wilson_lower_bound(500, 500)
    assert wilson_lower_bound(500, 500) - wilson_lower_bound(10, 10) > 0.25


def test_wilson_does_not_collapse_where_wald_does():
    p_hat = 1.0
    wald_margin = Z_95 * math.sqrt(p_hat * (1 - p_hat) / 10)
    assert wald_margin == 0.0  # Wald: zero uncertainty from 10 samples

    lower, upper = wilson_interval(10, 10)
    assert upper == 1.0
    assert lower < 0.75  # Wilson: substantial residual uncertainty


def test_wilson_never_escapes_the_unit_interval():
    p_hat, n = 0.95, 20
    wald_upper = p_hat + Z_95 * math.sqrt(p_hat * (1 - p_hat) / n)
    assert wald_upper > 1.0  # nonsense

    for k in range(21):
        lower, upper = wilson_interval(k, 20)
        assert 0.0 <= lower <= upper <= 1.0


def test_zero_trials_is_maximal_uncertainty():
    assert wilson_interval(0, 0) == (0.0, 1.0)


def test_zero_successes_lower_bound_is_exactly_zero():
    lower, upper = wilson_interval(0, 50)
    assert lower == 0.0
    assert upper > 0.0


def test_all_successes_upper_bound_is_exactly_one():
    assert wilson_interval(50, 50)[1] == 1.0


def test_rejects_impossible_counts():
    with pytest.raises(ValueError):
        wilson_interval(11, 10)
    with pytest.raises(ValueError):
        wilson_interval(-1, 10)


def test_lower_bound_is_monotone_in_sample_size_at_fixed_rate():
    previous = -1.0
    for n in (10, 20, 50, 100, 500, 2000):
        current = wilson_lower_bound(int(0.9 * n), n)
        assert current > previous
        previous = current


def test_lower_bound_is_monotone_in_successes_at_fixed_n():
    previous = -1.0
    for k in range(101):
        current = wilson_lower_bound(k, 100)
        assert current >= previous
        previous = current


def test_interval_contains_the_point_estimate():
    for k, n in [(1, 10), (7, 13), (45, 50), (99, 100)]:
        lower, upper = wilson_interval(k, n)
        assert lower <= k / n <= upper


def test_interval_narrows_as_evidence_accumulates():
    widths = [
        wilson_interval(int(0.9 * n), n)[1] - wilson_interval(int(0.9 * n), n)[0]
        for n in (10, 100, 1000)
    ]
    assert widths[0] > widths[1] > widths[2]


@pytest.mark.parametrize("n", [1, 3, 17, 250, 10_000])
@pytest.mark.parametrize("frac", [0.0, 0.01, 0.5, 0.99, 1.0])
def test_always_finite_and_ordered(n, frac):
    lower, upper = wilson_interval(int(frac * n), n)
    assert math.isfinite(lower) and math.isfinite(upper)
    assert 0.0 <= lower <= upper <= 1.0


def test_matches_statsmodels_reference_implementation():
    """Cross-checked against an implementation nobody on this team wrote."""
    sm = pytest.importorskip("statsmodels.stats.proportion")
    z_exact = 1.959963984540054
    for n in (5, 40, 300):
        for k in (0, 1, n // 2, n - 1, n):
            expected_lo, expected_hi = sm.proportion_confint(k, n, alpha=0.05, method="wilson")
            lower, upper = wilson_interval(k, n, z=z_exact)
            assert lower == pytest.approx(max(0.0, expected_lo), abs=1e-9)
            assert upper == pytest.approx(min(1.0, expected_hi), abs=1e-9)