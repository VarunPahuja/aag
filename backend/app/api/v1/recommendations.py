"""Recommendation resource — what governance proposed, and the human
authorization step ADR-0004 requires before an increase takes effect.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from shared.enums import RecommendationStatus

from app.api.v1.pagination import PageParam, PageSizeParam, paginate
from app.deps import CurrentUserDep, require_role
from app.errors import (
    CONFLICT_RESPONSE,
    FORBIDDEN_RESPONSE,
    NOT_FOUND_RESPONSE,
    ApiError,
    not_found,
)
from app.fixtures.recommendations import RECOMMENDATIONS, RECOMMENDATIONS_BY_ID
from app.schemas.envelope import Page
from app.schemas.governance import RecommendationDecision, RecommendationOut
from app.schemas.user import Role

router = APIRouter(prefix="/recommendations", tags=["recommendations"])

# REVIEWER cannot approve or reject a recommendation (docs/lanes/vp.md, Thu 10
# Sept security-pass check: "Reviewer cannot approve") — only ADMIN may.
_admin_only = Depends(require_role(Role.ADMIN))


def _get_recommendation_or_404(rec_id: str) -> RecommendationOut:
    rec = RECOMMENDATIONS_BY_ID.get(rec_id)
    if rec is None:
        raise not_found(
            "recommendation_not_found", f"No recommendation {rec_id!r}.", {"recommendation_id": rec_id}
        )
    return rec


def _decide(rec_id: str, new_status: RecommendationStatus) -> RecommendationOut:
    rec = _get_recommendation_or_404(rec_id)
    if rec.status is not RecommendationStatus.PENDING:
        raise ApiError(
            status_code=409,
            code="recommendation_already_resolved",
            message=f"Recommendation {rec_id!r} is already {rec.status.value}, not PENDING.",
            detail={"recommendation_id": rec_id, "status": rec.status.value},
        )
    return rec.model_copy(update={"status": new_status})


@router.get("", response_model=Page[RecommendationOut])
def list_recommendations(
    user: CurrentUserDep, page: PageParam = 1, page_size: PageSizeParam = 20
) -> Page[RecommendationOut]:
    """List recommendations, newest first.

    Once implemented: `SELECT ... ORDER BY generated_at DESC`, with a
    `?status=PENDING` filter for the approvals queue view.
    """
    return paginate(list(reversed(RECOMMENDATIONS)), page, page_size)


@router.get("/{rec_id}", response_model=RecommendationOut, responses=NOT_FOUND_RESPONSE)
def get_recommendation(rec_id: str, user: CurrentUserDep) -> RecommendationOut:
    """Fetch one recommendation by id, including its full opinion panel."""
    return _get_recommendation_or_404(rec_id)


_mutation_responses = {**NOT_FOUND_RESPONSE, **FORBIDDEN_RESPONSE, **CONFLICT_RESPONSE}


@router.post(
    "/{rec_id}/approve",
    response_model=RecommendationOut,
    dependencies=[_admin_only],
    responses=_mutation_responses,
)
def approve_recommendation(rec_id: str, body: RecommendationDecision) -> RecommendationOut:
    """Authorize a pending INCREASE. ADMIN only.

    Once implemented: writes an `approvals` row (`decided_by`, `verdict`,
    `reason`, `decided_at`), flips `Recommendation.status` to `APPROVED`,
    and — in the same transaction — writes the new `policy_versions` row
    that actually changes `agents.current_limit`
    (docs/lanes/vp.md: "Never update agents.current_limit without writing a
    policy_versions row in the same transaction"). This stub validates the
    recommendation exists and is still `PENDING`, then returns a copy with
    `status=APPROVED` — it does not persist the change or write a policy
    version.
    """
    return _decide(rec_id, RecommendationStatus.APPROVED)


@router.post(
    "/{rec_id}/reject",
    response_model=RecommendationOut,
    dependencies=[_admin_only],
    responses=_mutation_responses,
)
def reject_recommendation(rec_id: str, body: RecommendationDecision) -> RecommendationOut:
    """Reject a pending recommendation. ADMIN only, same as approve.

    Once implemented: writes an `approvals` row with `verdict=REJECTED` and
    flips `Recommendation.status` to `REJECTED`. No policy version is
    written — the agent's limit does not change.
    """
    return _decide(rec_id, RecommendationStatus.REJECTED)
