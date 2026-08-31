"""Randomised property tests for the Policy Engine, modeled on
`trust/tests/test_wilson_properties.py`: instead of checking specific
numbers, these check properties that must hold for every possible input.
"""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st
from shared.constants import AUTONOMY_LADDER, MAX_RUNG
from shared.enums import AgentState

from app.policy.ceiling import clamp_recommendation
from app.policy.engine import evaluate_decision
from app.policy.types import Invoice, PolicyVersion

_valid_rungs = st.integers(min_value=0, max_value=MAX_RUNG)
_ladder_limits = st.sampled_from(AUTONOMY_LADDER)
_amounts = st.integers(min_value=-1_000_000, max_value=1_000_000)
_agent_states = st.sampled_from(list(AgentState))


@st.composite
def valid_policy_versions(draw) -> PolicyVersion:
    rung = draw(_valid_rungs)
    limit = AUTONOMY_LADDER[rung]
    state = draw(_agent_states)
    return PolicyVersion(
        agent_id="agent-01", limit=limit, rung=rung, agent_state=state, version_id="pv-001"
    )


@given(amount=_amounts, policy=valid_policy_versions())
def test_never_allows_an_amount_above_the_limit(amount: int, policy: PolicyVersion):
    decision = evaluate_decision(Invoice(invoice_id="inv-1", amount=amount), policy)
    if amount > policy.limit:
        assert decision.allowed is False


@given(amount=_amounts, policy=st.one_of(st.none(), valid_policy_versions()))
def test_allowed_implies_within_limit(amount: int, policy: PolicyVersion | None):
    # allowed=True is only ever reachable through the within-limit branch —
    # this is the contrapositive of "never allow escalation-worthy amounts."
    decision = evaluate_decision(Invoice(invoice_id="inv-1", amount=amount), policy)
    if decision.allowed:
        assert decision.within_limit is True
        assert amount <= policy.limit  # type: ignore[union-attr]


@given(amount=_amounts, policy=valid_policy_versions())
def test_determinism_under_arbitrary_inputs(amount: int, policy: PolicyVersion):
    invoice = Invoice(invoice_id="inv-1", amount=amount)
    assert evaluate_decision(invoice, policy) == evaluate_decision(invoice, policy)


@given(
    proposed=st.integers(min_value=0, max_value=1_000_000),
    supported=st.integers(min_value=0, max_value=1_000_000),
)
def test_clamp_never_rises_above_the_evidence_supported_limit(proposed: int, supported: int):
    result = clamp_recommendation(proposed, supported)
    assert result.final_limit <= supported


@given(
    proposed=st.integers(min_value=0, max_value=1_000_000),
    supported=st.integers(min_value=0, max_value=1_000_000),
)
def test_clamp_is_deterministic(proposed: int, supported: int):
    assert clamp_recommendation(proposed, supported) == clamp_recommendation(proposed, supported)
