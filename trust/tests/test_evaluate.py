"""The orchestrator, end to end. Not re-testing ladder/score logic in
isolation (that's test_ladder.py / test_score.py) -- this checks that
evaluate() wires the pieces together correctly and the contract's own
invariants hold on the assembled TrustEvaluation.
"""

from __future__ import annotations

import pytest
from shared.constants import AUTONOMY_LADDER, rung_of
from shared.contracts import AgentContext
from shared.enums import Action, AgentState, Direction, DriftSeverity

from tests.conftest import correct_approval, critical_error, escalation, noncritical_error, run
from trust_engine.constants import COOLDOWN_BETWEEN_INCREASES
from trust_engine.evaluate import evaluate


def test_cold_start_agent_produces_a_valid_evaluation():
    """No decisions at all -- must not crash, and must land at the floor, HOLD."""
    result = evaluate([], AgentContext())
    assert result.total_decisions == 0
    assert result.trust_score == 0.0
    assert result.direction is Direction.HOLD
    assert result.eligible_for_increase is False


def test_proven_agent_earns_exactly_one_rung():
    decisions = (
        run(60, correct_approval)
        + run(10, escalation, recommended=Action.APPROVE, ruling=Action.APPROVE)
    )
    context = AgentContext(current_limit=1000, decisions_since_last_change=COOLDOWN_BETWEEN_INCREASES)
    result = evaluate(decisions, context)
    assert result.direction is Direction.INCREASE
    assert result.recommended_limit == 2500
    assert result.recommended_rung == rung_of(2500)


def test_ten_perfect_decisions_earn_nothing():
    """The headline statistical claim, end to end: a perfect ten is not proof."""
    result = evaluate(run(10, correct_approval), AgentContext())
    assert result.direction is Direction.HOLD
    from shared.reason_codes import INSUFFICIENT_SAMPLE
    assert INSUFFICIENT_SAMPLE in result.reason_codes


def test_critical_error_triggers_an_immediate_clawback():
    decisions = run(50, correct_approval) + run(1, critical_error)
    context = AgentContext(current_limit=5000, decisions_since_last_change=COOLDOWN_BETWEEN_INCREASES)
    result = evaluate(decisions, context)
    assert result.direction is Direction.CLAWBACK
    assert result.recommended_limit == 2500
    assert result.drift.severity is DriftSeverity.CRITICAL


def test_sustained_degradation_triggers_a_confirmed_clawback():
    good = run(350, correct_approval)
    bad = run(20, correct_approval) + run(30, noncritical_error)
    context = AgentContext(current_limit=5000, decisions_since_last_change=COOLDOWN_BETWEEN_INCREASES)
    result = evaluate(good + bad, context)
    assert result.direction is Direction.CLAWBACK
    assert result.recommended_limit == 2500
    assert result.drift.severity is DriftSeverity.CONFIRMED


# --- the contract invariants ----------------------------------------------------------


@pytest.mark.parametrize("limit", AUTONOMY_LADDER)
def test_current_rung_always_matches_current_limit(limit):
    context = AgentContext(current_limit=limit)
    result = evaluate(run(20, correct_approval), context)
    assert result.current_rung == rung_of(limit)
    assert result.current_limit == limit


@pytest.mark.parametrize("limit", AUTONOMY_LADDER)
def test_recommended_rung_always_matches_recommended_limit(limit):
    context = AgentContext(current_limit=limit, decisions_since_last_change=COOLDOWN_BETWEEN_INCREASES)
    result = evaluate(run(200, correct_approval), context)
    assert rung_of(result.recommended_limit) == result.recommended_rung


def test_eligible_for_increase_can_be_true_while_direction_is_hold():
    """The exact invariant from TrustEvaluation's own docstring: earned the
    evidence, but the cooldown hasn't elapsed yet."""
    decisions = run(60, correct_approval)
    context = AgentContext(current_limit=1000, decisions_since_last_change=1)
    result = evaluate(decisions, context)
    assert result.eligible_for_increase is True
    assert result.direction is Direction.HOLD


def test_direction_increase_always_implies_eligible():
    decisions = run(60, correct_approval)
    context = AgentContext(current_limit=1000, decisions_since_last_change=COOLDOWN_BETWEEN_INCREASES)
    result = evaluate(decisions, context)
    if result.direction is Direction.INCREASE:
        assert result.eligible_for_increase is True


# --- determinism, agent_id, and state passthrough --------------------------------------


def test_evaluation_is_deterministic():
    decisions = run(80, correct_approval) + run(5, noncritical_error)
    context = AgentContext(current_limit=1000)
    a = evaluate(decisions, context)
    b = evaluate(decisions, context)
    assert a.trust_score == b.trust_score
    assert a.direction == b.direction
    assert a.reason_codes == b.reason_codes


def test_decision_order_does_not_matter():
    decisions = run(80, correct_approval) + run(5, noncritical_error)
    context = AgentContext(current_limit=1000)
    forward = evaluate(decisions, context)
    backward = evaluate(list(reversed(decisions)), context)
    assert forward.trust_score == backward.trust_score
    assert forward.direction == backward.direction


def test_agent_id_taken_from_the_decisions():
    decisions = run(10, correct_approval, sequence=0)
    result = evaluate(decisions, AgentContext())
    assert result.agent_id == decisions[0].agent_id


def test_empty_decisions_use_a_placeholder_agent_id():
    result = evaluate([], AgentContext())
    assert result.agent_id == "unknown"


def test_agent_state_is_passed_through_from_context():
    context = AgentContext(state=AgentState.RESTRICTED)
    result = evaluate(run(5, correct_approval), context)
    assert result.state is AgentState.RESTRICTED


def test_reason_codes_are_never_empty():
    for decisions, context in [
        ([], AgentContext()),
        (run(60, correct_approval), AgentContext(current_limit=1000, decisions_since_last_change=100)),
        (run(50, correct_approval) + run(1, critical_error), AgentContext(current_limit=5000)),
    ]:
        result = evaluate(decisions, context)
        assert len(result.reason_codes) > 0


def test_reason_codes_have_no_duplicates():
    decisions = run(60, correct_approval)
    result = evaluate(decisions, AgentContext(current_limit=1000, decisions_since_last_change=100))
    assert len(result.reason_codes) == len(set(result.reason_codes))