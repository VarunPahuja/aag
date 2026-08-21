"""Randomised property tests. Instead of checking specific numbers, these check
properties that must hold for EVERY possible input.
"""

from __future__ import annotations

import math

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from trust_engine.constants import Z_95
from trust_engine.stats.wilson import wilson_interval, wilson_lower_bound


@st.composite
def counts(draw, max_n: int = 5000):
    trials = draw(st.integers(min_value=0, max_value=max_n))
    successes = draw(st.integers(min_value=0, max_value=trials))
    return successes, trials


@given(counts())
@settings(max_examples=300)
def test_interval_is_always_a_valid_probability_range(data):
    successes, trials = data
    lower, upper = wilson_interval(successes, trials)
    assert math.isfinite(lower) and math.isfinite(upper)
    assert 0.0 <= lower <= upper <= 1.0


@given(counts())
@settings(max_examples=300)
def test_observed_rate_always_falls_inside_the_interval(data):
    successes, trials = data
    assume(trials > 0)
    lower, upper = wilson_interval(successes, trials)
    assert lower <= successes / trials <= upper


@given(counts())
@settings(max_examples=300)
def test_degenerate_endpoints_are_exact(data):
    successes, trials = data
    assume(trials > 0)
    lower, upper = wilson_interval(successes, trials)
    if successes == trials:
        assert upper == 1.0
        assert lower < 1.0
    if successes == 0:
        assert lower == 0.0
        assert upper > 0.0


@given(st.integers(min_value=1, max_value=2000), st.data())
@settings(max_examples=200)
def test_one_more_correct_decision_never_lowers_the_bound(trials, data):
    successes = data.draw(st.integers(min_value=0, max_value=trials - 1))
    assert wilson_lower_bound(successes + 1, trials) >= wilson_lower_bound(successes, trials)


@given(counts())
@settings(max_examples=200)
def test_successes_and_failures_are_mirror_images(data):
    """lower(k, n) == 1 - upper(n-k, n) — catches sign errors instantly."""
    successes, trials = data
    assume(trials > 0)
    lower, _ = wilson_interval(successes, trials)
    _, mirrored_upper = wilson_interval(trials - successes, trials)
    assert lower == pytest.approx(1.0 - mirrored_upper, abs=1e-12)


@given(counts())
@settings(max_examples=200)
def test_the_bound_is_never_optimistic(data):
    """The lower bound never exceeds the observed rate — it must be conservative."""
    successes, trials = data
    assume(trials > 0)
    assert wilson_lower_bound(successes, trials) <= successes / trials


@given(counts())
@settings(max_examples=200)
def test_higher_confidence_gives_a_wider_interval(data):
    successes, trials = data
    assume(trials > 0)
    at_95 = wilson_lower_bound(successes, trials, z=Z_95)
    at_99 = wilson_lower_bound(successes, trials, z=2.5758293035489004)
    assert at_99 <= at_95


@given(st.integers(min_value=-500, max_value=500), st.integers(min_value=-500, max_value=500))
@settings(max_examples=150)
def test_impossible_inputs_are_rejected_loudly(successes, trials):
    if trials < 0 or successes < 0 or successes > trials:
        with pytest.raises(ValueError):
            wilson_interval(successes, trials)
    else:
        wilson_interval(successes, trials)