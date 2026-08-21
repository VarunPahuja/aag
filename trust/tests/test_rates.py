"""The three denominators. If this file is right, the module's hardest idea is right."""

from __future__ import annotations

import pytest
from shared.enums import Action

from tests.conftest import (
    correct_approval,
    correct_rejection,
    critical_error,
    escalation,
    noncritical_error,
    run,
)
from trust_engine.stats.rates import (
    accuracy,
    error_breakdown,
    human_agreement,
    partition,
    utilization,
)


def test_escalation_is_excluded_from_accuracy_entirely():
    """20 correct acted decisions + 10 escalations must read as 20/20, not 20/30."""
    decisions = run(20, correct_approval) + run(10, escalation)
    acc = accuracy(decisions)
    assert (acc.successes, acc.trials) == (20, 20)


def test_escalation_does_not_dilute_the_wilson_bound():
    only_acted = run(20, correct_approval)
    with_escalations = run(20, correct_approval) + run(50, escalation)
    assert accuracy(only_acted).wilson_lower == pytest.approx(
        accuracy(with_escalations).wilson_lower
    )


def test_correctness_is_undefined_for_an_escalation():
    assert escalation().is_correct is None


def test_an_agent_that_escalates_everything_earns_nothing():
    """Accuracy over an empty set is undefined -> Wilson bound 0 -> no autonomy."""
    decisions = run(100, escalation)
    acc = accuracy(decisions)
    assert acc.trials == 0
    assert acc.point is None
    assert acc.wilson_lower == 0.0

    util = utilization(decisions)
    assert util.point == 0.0
    assert util.wilson_upper < 0.05


def test_utilization_denominator_includes_escalations():
    decisions = run(30, correct_approval) + run(70, escalation)
    util = utilization(decisions)
    assert (util.successes, util.trials) == (30, 100)
    assert util.point == pytest.approx(0.30)


def test_perfect_agent_that_never_escalates_has_full_utilization():
    util = utilization(run(50, correct_approval))
    assert util.point == 1.0
    assert util.wilson_lower > 0.92


def test_human_agreement_counts_only_ruled_escalations():
    decisions = (
        run(40, correct_approval)
        + run(6, escalation, recommended=Action.APPROVE, ruling=Action.APPROVE)
        + run(4, escalation, recommended=Action.APPROVE, ruling=Action.REJECT)
    )
    agree = human_agreement(decisions)
    assert (agree.successes, agree.trials) == (6, 10)


def test_unruled_escalations_are_excluded_not_counted_as_disagreement():
    decisions = (
        run(5, escalation, recommended=Action.APPROVE, ruling=Action.APPROVE)
        + run(20, escalation, recommended=Action.APPROVE, ruling=None)
    )
    agree = human_agreement(decisions)
    assert (agree.successes, agree.trials) == (5, 5)


def test_escalation_without_a_recommendation_carries_no_agreement_signal():
    decisions = run(10, escalation, recommended=None, ruling=Action.APPROVE)
    assert human_agreement(decisions).trials == 0


def test_agreement_is_independent_of_accuracy():
    decisions = (
        run(30, correct_approval)
        + run(10, escalation, recommended=Action.APPROVE, ruling=Action.REJECT)
    )
    assert accuracy(decisions).point == 1.0
    assert human_agreement(decisions).point == 0.0


def test_critical_error_is_only_wrongful_approval():
    assert critical_error().is_critical_error is True
    assert noncritical_error().is_critical_error is False
    assert correct_approval().is_critical_error is False
    assert escalation().is_critical_error is False


def test_under_approval_is_an_error_but_not_a_critical_one():
    d = noncritical_error()
    assert d.is_correct is False
    assert d.is_critical_error is False
    assert d.is_noncritical_error is True


def test_error_breakdown_separates_severities():
    decisions = run(80, correct_approval) + run(3, critical_error) + run(7, noncritical_error)
    errors = error_breakdown(decisions)
    assert (errors.critical, errors.noncritical) == (3, 7)
    assert errors.acted_total == 90
    assert errors.critical_rate == pytest.approx(3 / 90)


def test_both_error_kinds_reduce_accuracy_equally():
    """Severity weighting belongs in the trust score, NOT the accuracy denominator."""
    a = accuracy(run(90, correct_approval) + run(10, critical_error))
    b = accuracy(run(90, correct_approval) + run(10, noncritical_error))
    assert a.point == b.point == pytest.approx(0.90)


def test_partition_is_exhaustive_and_disjoint():
    decisions = (
        run(10, correct_approval) + run(5, correct_rejection)
        + run(3, critical_error) + run(2, noncritical_error) + run(8, escalation)
    )
    p = partition(decisions)
    assert len(p.acted) + len(p.escalated) == p.n_total == 28
    assert len(p.acted) == 20


def test_partition_orders_by_sequence_for_reproducibility():
    decisions = list(reversed(run(20, correct_approval)))
    sequences = [d.sequence for d in partition(decisions).all_decisions]
    assert sequences == sorted(sequences)


def test_empty_input_does_not_crash():
    assert accuracy([]).trials == 0
    assert utilization([]).trials == 0
    assert human_agreement([]).trials == 0
    assert error_breakdown([]).critical_rate == 0.0