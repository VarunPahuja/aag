"""Recommendation resource — what governance proposed, and the human
authorization step ADR-0004 requires before an increase takes effect.

`list_recommendations`/`get_recommendation` read the real `recommendations`
table (vp/trust-governance-wiring). `approve`/`reject` remain fixture-backed —
wiring the human-authorization write path (an `approvals` row plus
`apply_policy_version` in the same transaction) is separate, later work; see
this branch's own report for why leaving that split is a real, visible gap
rather than an oversight.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from shared.enums import RecommendationStatus
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.pagination import PageParam, PageSizeParam, paginate
from app.deps import CurrentUserDep, DbSessionDep, require_role
from app.errors import (
    CONFLICT_RESPONSE,
    FORBIDDEN_RESPONSE,
    NOT_FOUND_RESPONSE,
    ApiError,
    not_found,
)
from app.fixtures.recommendations import RECOMMENDATIONS_BY_ID
from app.models import Recommendation as RecommendationRow
from app.schemas.envelope import Page
from app.schemas.governance import RecommendationDecision, RecommendationOut
from app.schemas.user import Role
from app.services.governance import recommendation_out

router = APIRouter(prefix="/recommendations", tags=["recommendations"])

# REVIEWER cannot approve or reject a recommendation (docs/lanes/vp.md, Thu 10
# Sept security-pass check: "Reviewer cannot approve") — only ADMIN may.
_admin_only = Depends(require_role(Role.ADMIN))


def _get_recommendation_row_or_404(db: Session, rec_id: str) -> RecommendationRow:
    row = db.get(RecommendationRow, rec_id)
    if row is None:
        raise not_found(
            "recommendation_not_found", f"No recommendation {rec_id!r}.", {"recommendation_id": rec_id}
        )
    return row


def _get_recommendation_or_404(rec_id: str) -> RecommendationOut:
    """Still fixture-backed — only `approve`/`reject` below use this."""
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
    db: DbSessionDep, user: CurrentUserDep, page: PageParam = 1, page_size: PageSizeParam = 20
) -> Page[RecommendationOut]:
    """List recommendations, newest first."""
    rows = (
        db.execute(select(RecommendationRow).order_by(RecommendationRow.generated_at.desc()))
        .scalars()
        .all()
    )
    return paginate([recommendation_out(row) for row in rows], page, page_size)


@router.get("/{rec_id}", response_model=RecommendationOut, responses=NOT_FOUND_RESPONSE)
def get_recommendation(rec_id: str, user: CurrentUserDep, db: DbSessionDep) -> RecommendationOut:
    """Fetch one recommendation by id, including its full opinion panel."""
    return recommendation_out(_get_recommendation_row_or_404(db, rec_id))


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
