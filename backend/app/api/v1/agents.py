"""Agent resource — identity, current standing, policy history, trust evidence.

`list_agents`/`get_agent` read the real `agents` table — this branch wires
decision ingest plus agent read (docs/lanes/vp.md, decision-ingest branch).
Everything below them (`policy-versions`, `trust`, `trust/history`) is still
fixture-backed: out of scope here, wired alongside trust/governance/
recommendations in the next branch.
"""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.v1.pagination import PageParam, PageSizeParam, paginate
from app.deps import CurrentUserDep, DbSessionDep
from app.errors import NOT_FOUND_RESPONSE, not_found
from app.fixtures.agents import AGENTS
from app.fixtures.policy_versions import POLICY_VERSIONS
from app.fixtures.trust import TRUST_CURRENT, TRUST_HISTORY
from app.models import Agent, Decision, PolicyVersion
from app.schemas.agent import AgentContextOut, AgentOut, PolicyVersionOut
from app.schemas.envelope import Page
from app.schemas.trust import TrustEvaluationOut

router = APIRouter(prefix="/agents", tags=["agents"])


def _get_agent_or_404(agent_id: str) -> AgentOut:
    """Still fixture-backed — only the three fixture-only routes below use
    this; `list_agents`/`get_agent` have their own DB-backed lookup."""
    agent = AGENTS.get(agent_id)
    if agent is None:
        raise not_found("agent_not_found", f"No agent {agent_id!r}.", {"agent_id": agent_id})
    return agent


def _agent_context(db: Session, agent: Agent) -> AgentContextOut:
    """Real, derived from the tables that exist — `docs/lanes/vp.md`'s
    `agents` schema has no `AgentContext` columns of its own.
    `current_limit`/`state` are the agent row's own fields; the two decision
    counts are computed relative to whichever policy version is currently in
    force: `decisions_since_last_change` is every decision recorded at or
    after that version's `effective_from`; `decisions_since_clawback` is the
    same count, but only when that version was itself a clawback (a lower
    rung than the one before it) — `None` otherwise, meaning "no clawback
    recovery is currently pending."
    """
    versions = (
        db.execute(
            select(PolicyVersion)
            .where(PolicyVersion.agent_id == agent.id)
            .order_by(PolicyVersion.effective_from.desc())
            .limit(2)
        )
        .scalars()
        .all()
    )
    if not versions:
        return AgentContextOut(
            current_limit=agent.current_limit,
            decisions_since_last_change=0,
            decisions_since_clawback=None,
            state=agent.state,
        )

    current = versions[0]
    since_change = (
        db.execute(
            select(func.count())
            .select_from(Decision)
            .where(Decision.agent_id == agent.id, Decision.decided_at >= current.effective_from)
        ).scalar()
        or 0
    )

    is_clawback = len(versions) > 1 and current.rung < versions[1].rung
    since_clawback = since_change if is_clawback else None

    return AgentContextOut(
        current_limit=agent.current_limit,
        decisions_since_last_change=since_change,
        decisions_since_clawback=since_clawback,
        state=agent.state,
    )


def _agent_out(db: Session, agent: Agent) -> AgentOut:
    return AgentOut(
        id=agent.id,
        name=agent.name,
        current_limit=agent.current_limit,
        current_rung=agent.current_rung,
        state=agent.state,
        context=_agent_context(db, agent),
    )


@router.get("", response_model=Page[AgentOut])
def list_agents(
    db: DbSessionDep, user: CurrentUserDep, page: PageParam = 1, page_size: PageSizeParam = 20
) -> Page[AgentOut]:
    """List every governed agent, ordered by id."""
    agents = db.execute(select(Agent).order_by(Agent.id)).scalars().all()
    return paginate([_agent_out(db, agent) for agent in agents], page, page_size)


@router.get("/{agent_id}", response_model=AgentOut, responses=NOT_FOUND_RESPONSE)
def get_agent(agent_id: str, user: CurrentUserDep, db: DbSessionDep) -> AgentOut:
    """Fetch one agent by id, including its current `AgentContext`."""
    agent = db.get(Agent, agent_id)
    if agent is None:
        raise not_found("agent_not_found", f"No agent {agent_id!r}.", {"agent_id": agent_id})
    return _agent_out(db, agent)


@router.get(
    "/{agent_id}/policy-versions", response_model=Page[PolicyVersionOut], responses=NOT_FOUND_RESPONSE
)
def list_policy_versions(
    agent_id: str, user: CurrentUserDep, page: PageParam = 1, page_size: PageSizeParam = 20
) -> Page[PolicyVersionOut]:
    """The agent's append-only limit history, newest first.

    Once implemented: `SELECT ... WHERE agent_id = :agent_id ORDER BY
    effective_from DESC`. `previous_version_id` always chains to a row
    that exists, except the very first version for an agent.
    """
    _get_agent_or_404(agent_id)
    versions = list(reversed(POLICY_VERSIONS.get(agent_id, [])))
    return paginate(versions, page, page_size)


@router.get("/{agent_id}/trust", response_model=TrustEvaluationOut, responses=NOT_FOUND_RESPONSE)
def get_current_trust(agent_id: str, user: CurrentUserDep) -> TrustEvaluationOut:
    """The agent's most recent `TrustEvaluation`.

    Once implemented: calls `trust_engine.evaluate(decisions, context)` with
    the agent's full decision history and current `AgentContext`, persists
    the result with a minted `id`, and returns it — or, if evaluation is
    cached, the most recent persisted row.
    """
    _get_agent_or_404(agent_id)
    evaluation = TRUST_CURRENT.get(agent_id)
    if evaluation is None:
        raise not_found(
            "trust_evaluation_not_found",
            f"No trust evaluation exists yet for agent {agent_id!r}.",
            {"agent_id": agent_id},
        )
    return evaluation


@router.get(
    "/{agent_id}/trust/history", response_model=Page[TrustEvaluationOut], responses=NOT_FOUND_RESPONSE
)
def list_trust_history(
    agent_id: str, user: CurrentUserDep, page: PageParam = 1, page_size: PageSizeParam = 20
) -> Page[TrustEvaluationOut]:
    """Every `TrustEvaluation` ever computed for this agent, newest first —
    what the dashboard's trust-over-time chart is built from.

    Once implemented: `SELECT ... WHERE agent_id = :agent_id ORDER BY
    evaluated_at DESC`.
    """
    _get_agent_or_404(agent_id)
    history = list(reversed(TRUST_HISTORY.get(agent_id, [])))
    return paginate(history, page, page_size)
