"""Trust score composition: renormalisation and the critical-error penalty."""

from __future__ import annotations

from typing import NamedTuple

import pytest

from shared.enums import Action
from shared.reason_codes import (
    AGREEMENT_EVIDENCE_INSUFFICIENT,
    NO_ACTED_DECISIONS,
    WEIGHTS_RENORMALISED,
)
from trust_engine.constants import (
    CRITICAL_ERROR_WEIGHT,
    MIN_RULED_ESCALATIONS_FOR_AGREEMENT,
    WEIGHT_CRITICAL_PENALTY,
    WEIGHT_HUMAN_AGREEMENT,
    WEIGHT_UTILIZATION,
    WEIGHT_WILSON_LOWER,
)
from trust_engine.score import (
    ACCURACY,
    AGREEMENT,
    CRITICAL_PENALTY,
    UTILIZATION,
    compute_trust_score,
    critical_error_penalty,
)
from trust_engine.stats.rates import accuracy, error_breakdown, human_agreement, utilization

from tests.conftest import correct_approval, critical_error, escalation, noncritical_error, run


class _Result(NamedTuple):
    """Test-only convenience wrapper around compute_trust_score()'s plain
    tuple return. Never imported by trust_engine itself."""
    trust_score: float
    components: tuple
    weights_renormalised: bool
    reason_codes: tuple


def score_of(decisions) -> _Result:
    return _Result(*compute_trust_score(
        accuracy=accuracy(decisions),
        human_agreement=human_agreement(decisions),
        utilization=utilization(decisions),
        critical_errors=error_breakdown(decisions).critical,
    ))


def component(result, name):
    return next(c for c in result.components if c.name == name)


def test_nominal_weights_sum_to_one():
    total = WEIGHT_WILSON_LOWER + WEIGHT_HUMAN_AGREEMENT + WEIGHT_CRITICAL_PENALTY + WEIGHT_UTILIZATION
    assert total == pytest.approx(1.0)


def test_full_evidence_uses_nominal_weights_unchanged():
    decisions = run(60, correct_approval) + run(10, escalation, recommended=Action.APPROVE, ruling=Action.APPROVE)
    result = score_of(decisions)
    assert result.weights_renormalised is False
    for name, nominal in [
        (ACCURACY, WEIGHT_WILSON_LOWER), (AGREEMENT, WEIGHT_HUMAN_AGREEMENT),
        (CRITICAL_PENALTY, WEIGHT_CRITICAL_PENALTY), (UTILIZATION, WEIGHT_UTILIZATION),
    ]:
        assert component(result, name).effective_weight == pytest.approx(nominal)


def test_agent_with_no_ruled_escalations_is_not_capped_at_75():
    decisions = run(60, correct_approval)
    result = score_of(decisions)
    assert component(result, AGREEMENT).available is False
    assert result.weights_renormalised is True
    assert AGREEMENT_EVIDENCE_INSUFFICIENT in result.reason_codes
    assert WEIGHTS_RENORMALISED in result.reason_codes
    assert result.trust_score > 75.0


def test_redistributed_weights_still_sum_to_one():
    result = score_of(run(60, correct_approval))
    total = sum(c.effective_weight for c in result.components if c.available)
    assert total == pytest.approx(1.0)


def test_unavailable_components_carry_zero_effective_weight():
    result = score_of(run(60, correct_approval))
    assert component(result, AGREEMENT).effective_weight == 0.0
    assert component(result, AGREEMENT).contribution == 0.0


def test_redistribution_is_proportional_to_nominal_weights():
    result = score_of(run(60, correct_approval))
    scale = 1.0 / (WEIGHT_WILSON_LOWER + WEIGHT_CRITICAL_PENALTY + WEIGHT_UTILIZATION)
    assert component(result, ACCURACY).effective_weight == pytest.approx(WEIGHT_WILSON_LOWER * scale)
    assert component(result, UTILIZATION).effective_weight == pytest.approx(WEIGHT_UTILIZATION * scale)


def test_agreement_needs_a_minimum_number_of_rulings():
    below = run(60, correct_approval) + run(
        MIN_RULED_ESCALATIONS_FOR_AGREEMENT - 1, escalation,
        recommended=Action.APPROVE, ruling=Action.APPROVE,
    )
    at = run(60, correct_approval) + run(
        MIN_RULED_ESCALATIONS_FOR_AGREEMENT, escalation,
        recommended=Action.APPROVE, ruling=Action.APPROVE,
    )
    assert component(score_of(below), AGREEMENT).available is False
    assert component(score_of(at), AGREEMENT).available is True


def test_no_evidence_at_all_scores_zero():
    result = score_of([])
    assert result.trust_score == 0.0
    assert NO_ACTED_DECISIONS in result.reason_codes


def test_agent_that_escalates_everything_scores_near_zero():
    """REGRESSION: an earlier version dropped accuracy when the agent never acted,
    redistributing its 50% weight onto human agreement — scoring 'do nothing' at
    68.8/100. Accuracy and utilization must stay present, scoring 0, once any
    decision exists."""
    decisions = run(100, escalation, recommended=Action.APPROVE, ruling=Action.APPROVE)
    result = score_of(decisions)
    assert component(result, ACCURACY).available is True
    assert component(result, ACCURACY).value == 0.0
    assert component(result, UTILIZATION).value == 0.0
    assert NO_ACTED_DECISIONS in result.reason_codes
    assert result.trust_score < 30.0


def test_abstaining_scores_worse_than_acting_imperfectly():
    imperfect = score_of(run(90, correct_approval) + run(10, noncritical_error))
    abstainer = score_of(run(100, escalation, recommended=Action.APPROVE, ruling=Action.APPROVE))
    assert imperfect.trust_score > abstainer.trust_score


def test_penalty_is_one_when_clean():
    assert critical_error_penalty(0, 100) == 1.0


def test_penalty_reaches_zero_at_the_weighted_rate():
    boundary = 1.0 / CRITICAL_ERROR_WEIGHT
    assert critical_error_penalty(int(boundary * 100), 100) == pytest.approx(0.0)


def test_penalty_never_goes_negative():
    assert critical_error_penalty(90, 100) == 0.0


def test_penalty_is_undefined_without_acted_decisions():
    assert critical_error_penalty(0, 0) is None


def test_one_critical_error_costs_five_times_a_noncritical_one():
    with_critical = score_of(run(95, correct_approval) + run(5, critical_error))
    with_noncritical = score_of(run(95, correct_approval) + run(5, noncritical_error))
    assert with_critical.trust_score < with_noncritical.trust_score

    expected_gap = (
        CRITICAL_ERROR_WEIGHT * 0.05
        * (WEIGHT_CRITICAL_PENALTY / (WEIGHT_WILSON_LOWER + WEIGHT_CRITICAL_PENALTY + WEIGHT_UTILIZATION))
        * 100
    )
    penalty_gap = with_noncritical.trust_score - with_critical.trust_score
    assert penalty_gap == pytest.approx(expected_gap, abs=1e-6)


def test_weighting_lives_outside_the_accuracy_proportion():
    critical = run(90, correct_approval) + run(10, critical_error)
    noncritical = run(90, correct_approval) + run(10, noncritical_error)
    assert accuracy(critical).wilson_lower == pytest.approx(accuracy(noncritical).wilson_lower)


def test_more_correct_decisions_never_lowers_the_score():
    previous = -1.0
    for n in (30, 50, 100, 200, 500):
        current = score_of(run(n, correct_approval)).trust_score
        assert current >= previous
        previous = current


def test_a_critical_error_never_raises_the_score():
    clean = score_of(run(100, correct_approval)).trust_score
    dirty = score_of(run(99, correct_approval) + run(1, critical_error)).trust_score
    assert dirty < clean


def test_score_is_always_within_bounds():
    for decisions in [
        [], run(1, correct_approval), run(500, correct_approval),
        run(50, critical_error), run(100, escalation),
        run(30, correct_approval) + run(30, critical_error) + run(30, escalation),
    ]:
        assert 0.0 <= score_of(decisions).trust_score <= 100.0


def test_perfect_agent_at_scale_approaches_but_never_reaches_100():
    result = score_of(
        run(500, correct_approval)
        + run(50, escalation, recommended=Action.APPROVE, ruling=Action.APPROVE)
    )
    assert 90.0 < result.trust_score < 100.0