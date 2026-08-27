"""Agent, policy-version, and agent-context response models.

`AgentContextOut` mirrors `shared.contracts.AgentContext` field-for-field.
`AgentOut` and `PolicyVersionOut` have no `shared/` equivalent — they are
backend-local resources (docs/lanes/vp.md's `agents` / `policy_versions`
tables) that exist to be read over HTTP, not passed to the trust engine
directly. `AgentOut.context` is what a caller assembles into an
`AgentContext` before calling `trust_engine.evaluate()`.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict
from shared.enums import AgentState


class AgentContextOut(BaseModel):
    """Mirrors `shared.contracts.AgentContext` field-for-field."""

    model_config = ConfigDict(from_attributes=True)

    current_limit: int
    decisions_since_last_change: int
    decisions_since_clawback: int | None
    state: AgentState


class AgentOut(BaseModel):
    """A governed agent. Backend-local resource — no `shared/` equivalent.

    `current_rung`/`current_limit` are always kept in sync with
    `shared.constants.rung_of`/`limit_of` (the invariant `TrustEvaluation`
    documents applies here too, since this is the same pair of numbers).
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    current_limit: int
    current_rung: int
    state: AgentState
    context: AgentContextOut


class PolicyVersionOut(BaseModel):
    """One row of an agent's append-only limit history.

    docs/lanes/vp.md: "`policy_versions` is append-only and every decision
    references one" — this is what `GET /agents/{agent_id}/policy-versions`
    returns, oldest-relevant invariant first: `previous_version_id` chains
    each row to the one it replaced, `None` only on an agent's very first
    version.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    agent_id: str
    limit: int
    rung: int
    effective_from: datetime
    created_by: str
    reason: str
    previous_version_id: str | None
