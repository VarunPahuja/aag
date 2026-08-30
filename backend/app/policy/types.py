"""Plain data the Policy Engine consumes and produces.

Deliberately not `shared.contracts.DecisionRecord` (the simulator's output —
a different shape for a different consumer, the trust engine) and deliberately
not an ORM row from `backend/app/models/` (this module may import no database
code at all, ADR-0003 / ADR-0014). `Invoice` and `PolicyVersion` here are the
minimal views the engine needs; whatever calls `evaluate_decision` is
responsible for assembling them from wherever the real data lives.

`AgentState` comes from `shared.enums` — that import is fine. It is a plain
`str, Enum` subclass with no database, network, or LLM dependency of its own,
so depending on it does not compromise the module's purity; it only makes
`PolicyVersion.agent_state` type-correct instead of a bare string that could
drift from the values `AgentState` actually has.
"""

from __future__ import annotations

from dataclasses import dataclass

from shared.enums import AgentState


@dataclass(frozen=True, slots=True)
class Invoice:
    """The minimal shape `evaluate_decision` needs from an invoice."""

    invoice_id: str
    amount: int


@dataclass(frozen=True, slots=True)
class PolicyVersion:
    """The policy in force at decision time: the agent's ceiling, rung, and
    operating state, bundled into one immutable view. Mirrors the shape of
    `app.models.policy_versions.PolicyVersion` plus `Agent.state`, but is its
    own type — the Policy Engine never imports that ORM model.
    """

    agent_id: str
    limit: int
    rung: int
    agent_state: AgentState
    version_id: str


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    """What the Policy Engine decided, and why.

    `within_limit` is the pure numeric fact — amount vs. ceiling — independent
    of `allowed`. A suspended agent under its limit is `within_limit=True` but
    `allowed=False`: the amount was fine, the agent wasn't. This split matters
    downstream because `decisions.within_limit` (docs/lanes/vp.md) is its own
    column, recorded regardless of why the agent could or couldn't act on it.

    When the engine cannot confidently evaluate a case at all (a missing or
    invalid policy version), `within_limit` is `False` too — fail-closed
    means refusing to vouch for the amount being fine, not just refusing to
    allow the action.
    """

    allowed: bool
    within_limit: bool
    reason_code: str
