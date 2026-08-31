"""`evaluate_decision` — every branch, every reason code, every boundary.

Matches the standard set in trust/'s own test suite: real numeric assertions
with expected values, not "assert it does not raise."
"""

from __future__ import annotations

from shared.enums import AgentState

from app.policy import reason_codes
from app.policy.engine import evaluate_decision
from app.policy.types import Invoice, PolicyVersion

AGENT_ID = "agent-01"


def _policy(*, limit: int, rung: int, agent_state: AgentState = AgentState.ACTIVE) -> PolicyVersion:
    return PolicyVersion(
        agent_id=AGENT_ID, limit=limit, rung=rung, agent_state=agent_state, version_id="pv-001"
    )


def _invoice(amount: int) -> Invoice:
    return Invoice(invoice_id="inv-001", amount=amount)


# --- amount vs. limit -------------------------------------------------------------


def test_amount_within_limit_is_allowed():
    decision = evaluate_decision(_invoice(300), _policy(limit=500, rung=0))
    assert decision.allowed is True
    assert decision.within_limit is True
    assert decision.reason_code == reason_codes.WITHIN_LIMIT


def test_amount_exceeding_limit_escalates():
    decision = evaluate_decision(_invoice(501), _policy(limit=500, rung=0))
    assert decision.allowed is False
    assert decision.within_limit is False
    assert decision.reason_code == reason_codes.LIMIT_EXCEEDED


def test_amount_exactly_at_limit_is_allowed_inclusive_boundary():
    # docs/lanes/vp.md: "allowed to approve up to ₹500" — inclusive of ₹500
    # itself. See evaluate_decision's docstring for the full argument.
    decision = evaluate_decision(_invoice(500), _policy(limit=500, rung=0))
    assert decision.allowed is True
    assert decision.within_limit is True
    assert decision.reason_code == reason_codes.WITHIN_LIMIT


def test_amount_one_rupee_over_the_limit_escalates():
    decision = evaluate_decision(_invoice(2501), _policy(limit=2500, rung=2))
    assert decision.allowed is False
    assert decision.within_limit is False
    assert decision.reason_code == reason_codes.LIMIT_EXCEEDED


# --- agent state -------------------------------------------------------------------


def test_suspended_agent_escalates_even_for_a_tiny_amount():
    decision = evaluate_decision(
        _invoice(1), _policy(limit=10000, rung=4, agent_state=AgentState.SUSPENDED)
    )
    assert decision.allowed is False
    assert decision.reason_code == reason_codes.AGENT_SUSPENDED
    # The amount itself was fine — the agent's state is why this escalates.
    assert decision.within_limit is True


def test_restricted_agent_escalates_even_for_a_tiny_amount():
    decision = evaluate_decision(
        _invoice(1), _policy(limit=10000, rung=4, agent_state=AgentState.RESTRICTED)
    )
    assert decision.allowed is False
    assert decision.reason_code == reason_codes.AGENT_RESTRICTED
    assert decision.within_limit is True


def test_suspended_agent_over_limit_reports_suspended_not_limit_exceeded():
    # State is checked before the limit comparison decides the outcome —
    # suspension is the reason this escalates, not the (also true) fact that
    # the amount exceeds the limit.
    decision = evaluate_decision(
        _invoice(999999), _policy(limit=500, rung=0, agent_state=AgentState.SUSPENDED)
    )
    assert decision.allowed is False
    assert decision.reason_code == reason_codes.AGENT_SUSPENDED
    assert decision.within_limit is False


def test_probation_agent_within_limit_is_allowed():
    # PROBATION is not one of the two escalate-regardless-of-amount states —
    # it behaves exactly like ACTIVE for evaluate_decision's purposes.
    decision = evaluate_decision(
        _invoice(500), _policy(limit=500, rung=0, agent_state=AgentState.PROBATION)
    )
    assert decision.allowed is True
    assert decision.reason_code == reason_codes.WITHIN_LIMIT


# --- missing / invalid policy version -----------------------------------------------


def test_missing_policy_version_fails_closed():
    decision = evaluate_decision(_invoice(1), None)
    assert decision.allowed is False
    assert decision.within_limit is False
    assert decision.reason_code == reason_codes.POLICY_VERSION_MISSING


def test_zero_limit_policy_version_fails_closed():
    decision = evaluate_decision(_invoice(1), _policy(limit=0, rung=0))
    assert decision.allowed is False
    assert decision.reason_code == reason_codes.POLICY_VERSION_INVALID


def test_negative_limit_policy_version_fails_closed():
    decision = evaluate_decision(_invoice(1), _policy(limit=-500, rung=0))
    assert decision.allowed is False
    assert decision.reason_code == reason_codes.POLICY_VERSION_INVALID


def test_rung_out_of_range_fails_closed():
    decision = evaluate_decision(_invoice(1), _policy(limit=500, rung=99))
    assert decision.allowed is False
    assert decision.reason_code == reason_codes.POLICY_VERSION_INVALID


def test_rung_limit_mismatch_fails_closed():
    # 2500 is rung 2, not rung 1 (shared.constants.AUTONOMY_LADDER).
    decision = evaluate_decision(_invoice(1), _policy(limit=2500, rung=1))
    assert decision.allowed is False
    assert decision.reason_code == reason_codes.POLICY_VERSION_INVALID


def test_invalid_policy_version_never_reports_within_limit_true():
    # Fail-closed extends to within_limit too: an engine that can't vouch for
    # the policy shouldn't vouch for the amount against it either, even if
    # the amount happens to look small.
    decision = evaluate_decision(_invoice(1), _policy(limit=-500, rung=0))
    assert decision.within_limit is False


# --- every ladder rung, exercised explicitly -----------------------------------------


def test_every_ladder_rung_allows_at_its_own_ceiling():
    for rung, limit in enumerate((500, 1000, 2500, 5000, 10000)):
        decision = evaluate_decision(_invoice(limit), _policy(limit=limit, rung=rung))
        assert decision.allowed is True, f"rung {rung} (limit {limit}) should allow at its ceiling"
        assert decision.reason_code == reason_codes.WITHIN_LIMIT


def test_every_ladder_rung_escalates_one_rupee_over_its_ceiling():
    for rung, limit in enumerate((500, 1000, 2500, 5000, 10000)):
        decision = evaluate_decision(_invoice(limit + 1), _policy(limit=limit, rung=rung))
        assert decision.allowed is False, (
            f"rung {rung} (limit {limit}) should escalate over ceiling"
        )
        assert decision.reason_code == reason_codes.LIMIT_EXCEEDED


# --- determinism ---------------------------------------------------------------------


def test_same_inputs_produce_identical_output_every_time():
    invoice = _invoice(2500)
    policy = _policy(limit=2500, rung=2)
    first = evaluate_decision(invoice, policy)
    second = evaluate_decision(invoice, policy)
    third = evaluate_decision(invoice, policy)
    assert first == second == third
