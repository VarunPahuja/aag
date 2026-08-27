"""Agent resource — identity, current standing, policy history, trust evidence.

Every route here returns canned data from `app/fixtures/`. Real
implementations land with persistence (docs/DEADLINES.md: Fri 28 Aug /
Mon 31 Aug) — each docstring says what that will look like.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.pagination import PageParam, PageSizeParam, paginate
from app.deps import CurrentUserDep
from app.errors import NOT_FOUND_RESPONSE, not_found
from app.fixtures.agents import AGENTS
from app.fixtures.policy_versions import POLICY_VERSIONS
from app.fixtures.trust import TRUST_CURRENT, TRUST_HISTORY
from app.schemas.agent import AgentOut, PolicyVersionOut
from app.schemas.envelope import Page
from app.schemas.trust import TrustEvaluationOut

router = APIRouter(prefix="/agents", tags=["agents"])


def _get_agent_or_404(agent_id: str) -> AgentOut:
    agent = AGENTS.get(agent_id)
    if agent is None:
        raise not_found("agent_not_found", f"No agent {agent_id!r}.", {"agent_id": agent_id})
    return agent


@router.get("", response_model=Page[AgentOut])
def list_agents(
    user: CurrentUserDep, page: PageParam = 1, page_size: PageSizeParam = 20
) -> Page[AgentOut]:
    """List every governed agent.

    Once implemented: a `SELECT` over `agents`, ordered by `id`, paginated
    with `LIMIT`/`OFFSET`. No filtering by state yet — add `?state=` if the
    dashboard needs it before persistence lands.
    """
    return paginate(list(AGENTS.values()), page, page_size)


@router.get("/{agent_id}", response_model=AgentOut, responses=NOT_FOUND_RESPONSE)
def get_agent(agent_id: str, user: CurrentUserDep) -> AgentOut:
    """Fetch one agent by id, including its current `AgentContext`.

    Once implemented: a `SELECT ... WHERE id = :agent_id`, 404 if no row.
    """
    return _get_agent_or_404(agent_id)


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
