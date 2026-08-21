"""Drift detection: the two-stage tripwire + significance test."""

from __future__ import annotations

import pytest
from shared.enums import DriftSeverity

from tests.conftest import correct_approval, critical_error, escalation, noncritical_error, run
from trust_engine.stats.drift import (
    accuracy_counts,
    critical_errors_in_window,
    detect_drift,
    split_history,
    two_proportion_z,
)


def test_identical_rates_give_zero_z():
    z, p = two_proportion_z(45, 50, 450, 500)
    assert z == pytest.approx(0.0, abs=1e-9)
    assert p == pytest.approx(0.5, abs=1e-9)


def test_worse_recent_performance_gives_negative_z():
    z, p = two_proportion_z(30, 50, 470, 500)
    assert z < 0
    assert p < 0.001


def test_better_recent_performance_gives_positive_z_and_high_p():
    """Improvement is not drift. One-sided p stays high so nothing fires."""
    z, p = two_proportion_z(50, 50, 400, 500)
    assert z > 0
    assert p > 0.95


def test_zero_variance_is_handled_not_divided_by():
    assert two_proportion_z(50, 50, 500, 500) == (0.0, 1.0)


def test_empty_samples_return_neutral():
    assert two_proportion_z(0, 0, 10, 10) == (0.0, 1.0)


def test_split_puts_the_last_n_in_recent():
    decisions = run(120, correct_approval)
    baseline, recent = split_history(decisions, window=50)
    assert len(recent) == 50
    assert len(baseline) == 70
    assert max(d.sequence for d in baseline) < min(d.sequence for d in recent)


def test_too_few_decisions_means_no_baseline():
    baseline, recent = split_history(run(20, correct_approval), window=50)
    assert baseline == []
    assert len(recent) == 20


def test_accuracy_counts_ignore_escalations():
    decisions = run(30, correct_approval) + run(10, escalation)
    assert accuracy_counts(decisions) == (30, 30)


def test_steady_performance_shows_no_drift():
    decisions = run(200, correct_approval)
    result = detect_drift(decisions)
    assert result.detected is False
    assert result.severity is DriftSeverity.NONE


def test_large_sustained_drop_is_confirmed():
    """350 good then 50 bad: tripwire fires AND the z-test agrees."""
    good = run(350, correct_approval)
    bad = run(20, correct_approval) + run(30, noncritical_error)
    result = detect_drift(good + bad)
    assert result.severity is DriftSeverity.CONFIRMED
    assert result.drop_pp > 10.0
    assert result.z_statistic < 0
    assert result.p_value < 0.05


def test_a_critical_error_short_circuits_everything():
    decisions = run(300, correct_approval) + run(1, critical_error)
    result = detect_drift(decisions)
    assert result.severity is DriftSeverity.CRITICAL
    assert result.critical_errors_in_window == 1


def test_small_drop_below_the_tripwire_does_not_fire():
    good = run(300, correct_approval)
    slightly_worse = run(46, correct_approval) + run(4, noncritical_error)
    result = detect_drift(good + slightly_worse)
    assert result.severity is DriftSeverity.NONE
    assert result.drop_pp < 10.0


def test_underpowered_sample_warns_but_does_not_confirm():
    good = run(35, correct_approval)
    bad = run(5, noncritical_error)
    result = detect_drift(good + bad, recent_window=10, min_n=30)
    assert result.detected is True
    assert result.severity is DriftSeverity.WARNING
    assert result.underpowered is True


def test_no_baseline_means_no_drift():
    result = detect_drift(run(10, noncritical_error))
    assert result.detected is False
    assert result.baseline_accuracy is None


def test_critical_error_window_only_looks_at_recent_acted_decisions():
    old_error = run(1, critical_error) + run(100, correct_approval)
    assert critical_errors_in_window(old_error, window=20) == 0

    new_error = run(100, correct_approval) + run(1, critical_error)
    assert critical_errors_in_window(new_error, window=20) == 1


def test_escalations_cannot_hide_a_critical_error():
    decisions = run(50, correct_approval) + run(1, critical_error) + run(40, escalation)
    assert critical_errors_in_window(decisions, window=20) == 1