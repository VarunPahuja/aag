"""Three agents, one coherent story, built directly from `shared.contracts`.

- **agent-01** — mid-ladder (rung 2, ₹2,500), strong evidence, eligible for
  and recommended an increase to rung 3 (₹5,000). Rung/limit pairs are
  always real `AUTONOMY_LADDER` values, never invented numbers.
- **agent-02** — on probation at the floor, still gathering evidence
  (`acted_decisions` below `MIN_SAMPLE_FOR_INCREASE`).
- **agent-03** — was at rung 2, confirmed drift triggered an automatic
  clawback to rung 1 (₹1,000); now recovering.

Every agent id used anywhere else in `app/fixtures/` (decisions, trust
evaluations, recommendations, audit samples) is one of these three — kept
consistent on purpose so Adhya's dashboard tells one coherent story instead
of three unrelated stubs.
"""

from __future__ import annotations

from shared.constants import limit_of, rung_of
from shared.contracts import AgentContext
from shared.enums import AgentState

from app.schemas.agent import AgentContextOut, AgentOut

AGENT_IDS: tuple[str, ...] = ("agent-01", "agent-02", "agent-03")

_CONTEXTS: dict[str, AgentContext] = {
    "agent-01": AgentContext(
        current_limit=limit_of(2),
        decisions_since_last_change=120,
        decisions_since_clawback=None,
        state=AgentState.ACTIVE,
    ),
    "agent-02": AgentContext(
        current_limit=limit_of(0),
        decisions_since_last_change=12,
        decisions_since_clawback=None,
        state=AgentState.PROBATION,
    ),
    "agent-03": AgentContext(
        current_limit=limit_of(1),  # already clawed back from rung 2 to rung 1
        decisions_since_last_change=5,
        decisions_since_clawback=5,  # recovering; CLEAN_DECISIONS_AFTER_CLAWBACK is trust/'s gate
        state=AgentState.RESTRICTED,
    ),
}

_NAMES: dict[str, str] = {
    "agent-01": "Invoice Agent — Procurement",
    "agent-02": "Invoice Agent — Facilities",
    "agent-03": "Invoice Agent — Marketing",
}


def _agent_out(agent_id: str) -> AgentOut:
    ctx = _CONTEXTS[agent_id]
    return AgentOut(
        id=agent_id,
        name=_NAMES[agent_id],
        current_limit=ctx.current_limit,
        current_rung=rung_of(ctx.current_limit),
        state=ctx.state,
        context=AgentContextOut.model_validate(ctx, from_attributes=True),
    )


AGENTS: dict[str, AgentOut] = {agent_id: _agent_out(agent_id) for agent_id in AGENT_IDS}
