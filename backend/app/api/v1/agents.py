"""Agent resource — identity, current standing, policy history, trust
evidence, and the governance recommendations generated from it.

`list_agents`/`get_agent`/`trust`/`trust/history`/`recommendations` read and
write the real tables (docs/lanes/vp.md; decision-ingest, then
vp/trust-governance-wiring). Only `policy-versions` remains fixture-backed —
out of scope here.
"""

from __future__ import annotations

import dataclasses

from fastapi import APIRouter, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.pagination import PageParam, PageSizeParam, paginate
from app.deps import CurrentUserDep, DbSessionDep
from app.errors import NOT_FOUND_RESPONSE, SERVICE_UNAVAILABLE_RESPONSE, not_found
from app.fixtures.agents import AGENTS
from app.fixtures.policy_versions import POLICY_VERSIONS
from app.models import Agent
from app.models import TrustEvaluation as TrustEvaluationRow
from app.schemas.agent import AgentOut, PolicyVersionOut
from app.schemas.envelope import Page
from app.schemas.governance import RecommendationOut
from app.schemas.trust import TrustEvaluationOut
from app.services.governance import generate_recommendation
from app.services.trust import agent_context, compute_and_persist_trust_evaluation

router = APIRouter(prefix="/agents", tags=["agents"])


def _get_agent_or_404(agent_id: str) -> AgentOut:
    """Still fixture-backed — only `list_policy_versions` below uses this;
    every other route has its own DB-backed lookup."""
    agent = AGENTS.get(agent_id)
    if agent is None:
        raise not_found("agent_not_found", f"No agent {agent_id!r}.", {"agent_id": agent_id})
    return agent


def _get_agent_row_or_404(db: Session, agent_id: str) -> Agent:
    agent = db.get(Agent, agent_id)
    if agent is None:
        raise not_found("agent_not_found", f"No agent {agent_id!r}.", {"agent_id": agent_id})
    return agent


def _agent_out(db: Session, agent: Agent) -> AgentOut:
    return AgentOut(
        id=agent.id,
        name=agent.name,
        current_limit=agent.current_limit,
        current_rung=agent.current_rung,
        state=agent.state,
        context=agent_context(db, agent),
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
    return _agent_out(db, _get_agent_row_or_404(db, agent_id))


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
def get_current_trust(agent_id: str, user: CurrentUserDep, db: DbSessionDep) -> TrustEvaluationOut:
    """Evaluate `agent_id`'s real persisted decision history with the real
    trust engine, persist the result, and return it. An agent with zero
    decisions still gets a valid `TrustEvaluation` back — `trust_engine.evaluate`
    is designed to handle an empty history, not to be called only once one
    exists (see `app/services/trust.py`).
    """
    agent = _get_agent_row_or_404(db, agent_id)
    evaluation, row_id = compute_and_persist_trust_evaluation(db, agent)
    return TrustEvaluationOut(id=row_id, **dataclasses.asdict(evaluation))


@router.get(
    "/{agent_id}/trust/history", response_model=Page[TrustEvaluationOut], responses=NOT_FOUND_RESPONSE
)
def list_trust_history(
    agent_id: str, user: CurrentUserDep, db: DbSessionDep, page: PageParam = 1, page_size: PageSizeParam = 20
) -> Page[TrustEvaluationOut]:
    """Every `TrustEvaluation` ever persisted for this agent, newest first —
    what the dashboard's trust-over-time chart is built from."""
    _get_agent_row_or_404(db, agent_id)
    rows = (
        db.execute(
            select(TrustEvaluationRow)
            .where(TrustEvaluationRow.agent_id == agent_id)
            .order_by(TrustEvaluationRow.evaluated_at.desc())
        )
        .scalars()
        .all()
    )
    items = [TrustEvaluationOut(id=row.id, **row.payload) for row in rows]
    return paginate(items, page, page_size)


@router.post(
    "/{agent_id}/recommendations",
    response_model=RecommendationOut,
    status_code=status.HTTP_201_CREATED,
    responses={**NOT_FOUND_RESPONSE, **SERVICE_UNAVAILABLE_RESPONSE},
)
def create_recommendation(agent_id: str, user: CurrentUserDep, db: DbSessionDep) -> RecommendationOut:
    """Generate a fresh governance recommendation for `agent_id`: recompute
    its `TrustEvaluation` from persisted decisions, run the governance panel
    over it (`GOVERNANCE_MODE`, default `stub`), clamp the panel's proposal to
    what the evidence actually supports, and persist trust evaluation,
    recommendation, and audit entry — all in this one request's transaction
    (`app.deps.get_session`; see `app/services/governance.py`)."""
    agent = _get_agent_row_or_404(db, agent_id)
    return generate_recommendation(db, agent)
