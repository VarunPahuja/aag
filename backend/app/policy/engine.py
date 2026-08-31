"""The Policy Engine: the only code in this system that decides whether an
agent's action is permitted (ADR-0003, ADR-0014).

Hard rules, enforced by `backend/tests/test_policy_import_boundary.py`:
no database, no network, no LLM, no file I/O, no `os.environ` reads, no
wall-clock reads, no global mutable state. Every function here is pure —
identical inputs produce identical output, forever. Timestamps, if a caller
needs to record when a decision was evaluated, are the caller's problem: this
module never reads a clock.
"""

from __future__ import annotations

from shared.constants import MAX_RUNG, rung_of
from shared.enums import AgentState

from app.policy import reason_codes
from app.policy.types import Invoice, PolicyDecision, PolicyVersion

_ESCALATING_STATES: dict[AgentState, str] = {
    AgentState.SUSPENDED: reason_codes.AGENT_SUSPENDED,
    AgentState.RESTRICTED: reason_codes.AGENT_RESTRICTED,
}


def _is_valid(policy_version: PolicyVersion) -> bool:
    if policy_version.limit <= 0:
        return False
    if not (0 <= policy_version.rung <= MAX_RUNG):
        return False
    return rung_of(policy_version.limit) == policy_version.rung


def evaluate_decision(invoice: Invoice, policy_version: PolicyVersion | None) -> PolicyDecision:
    """May the agent act on `invoice` autonomously, or must it escalate?

    Checked in order, each one fatal (later checks never override an earlier
    escalation):

    1. Missing policy version -> escalate. Fail closed: no evidence of what
       the agent is allowed to do is not the same as unlimited permission.
    2. Invalid policy version (non-positive limit, rung out of range, or
       `rung_of(limit) != rung` — the same invariant `agents.current_rung`
       must hold) -> escalate. Fail closed again: a self-inconsistent policy
       is not one this engine will act on.
    3. Agent state SUSPENDED or RESTRICTED -> escalate regardless of amount.
       A human took the agent out of autonomous service; the amount is
       irrelevant to that decision.
    4. Amount exceeds the limit -> escalate.
    5. Amount equal to the limit -> ALLOWED. The ladder is phrased as "allowed
       to approve *up to* ₹500" (docs/lanes/vp.md) — an inclusive ceiling, not
       an exclusive one. An agent at the ₹500 rung may approve a ₹500
       invoice; ₹500.01 (or, since amounts are integer rupees here, ₹501)
       escalates.
    6. Otherwise (amount within the limit) -> ALLOWED.

    Fail-closed is the governing principle throughout: any condition this
    engine cannot confidently evaluate resolves to escalation, never to
    permission.
    """
    if policy_version is None:
        return PolicyDecision(
            allowed=False, within_limit=False, reason_code=reason_codes.POLICY_VERSION_MISSING
        )

    if not _is_valid(policy_version):
        return PolicyDecision(
            allowed=False, within_limit=False, reason_code=reason_codes.POLICY_VERSION_INVALID
        )

    within_limit = invoice.amount <= policy_version.limit

    state_reason = _ESCALATING_STATES.get(policy_version.agent_state)
    if state_reason is not None:
        return PolicyDecision(allowed=False, within_limit=within_limit, reason_code=state_reason)

    if not within_limit:
        return PolicyDecision(
            allowed=False, within_limit=False, reason_code=reason_codes.LIMIT_EXCEEDED
        )

    return PolicyDecision(allowed=True, within_limit=True, reason_code=reason_codes.WITHIN_LIMIT)
