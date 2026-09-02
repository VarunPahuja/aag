"""Recommendation resource — what governance proposed, and the human
authorization step ADR-0004 requires before an increase takes effect.

Every route here reads or writes the real tables. `approve`/`reject` are the
human-authorization write path: an `approvals` row, and — on approval only —
a new `policy_versions` row via `apply_policy_version`, all in the one
transaction `app.deps.get_session` commits or rolls back as a whole (the
same pattern `app/api/v1/decisions.py`'s decision-ingest and
`app/services/governance.py`'s recommendation generation already use).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from shared.constants import rung_of
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
from app.models import Agent, Approval, apply_policy_version
from app.models import Recommendation as RecommendationRow
from app.models.audit_log import append_entry
from app.schemas.envelope import Page
from app.schemas.governance import RecommendationDecision, RecommendationOut
from app.schemas.user import CurrentUser, Role
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


def _record_decision(
    db: Session,
    user: CurrentUser,
    rec_id: str,
    verdict: RecommendationStatus,
    reason: str,
) -> RecommendationOut:
    """The one transaction behind both `approve` and `reject`: load the
    recommendation, refuse to re-decide a resolved one, write the `approvals`
    row, flip the recommendation's status, and — on `APPROVED` only — apply
    the new policy version via `apply_policy_version` (the sanctioned path;
    `app/models/guards.py` refuses any other way to move
    `agents.current_limit`/`current_rung`). A single `audit_log` entry closes
    every path, approve or reject.

    `row.proposed_limit` is already the post-clamp value
    (`app/services/governance.py:generate_recommendation` stores
    `clamp_recommendation`'s `final_limit`, not governance's raw ask) — an
    approval can only ever move an agent to what the evidence supported, not
    what a panel proposed before the ceiling ran.
    """
    row = _get_recommendation_row_or_404(db, rec_id)
    if row.status is not RecommendationStatus.PENDING:
        raise ApiError(
            status_code=409,
            code="recommendation_already_resolved",
            message=f"Recommendation {rec_id!r} is already {row.status.value}, not PENDING.",
            detail={"recommendation_id": rec_id, "status": row.status.value},
        )

    decided_at = datetime.now(UTC)
    db.add(
        Approval(
            id=f"appr-{uuid.uuid4().hex[:12]}",
            recommendation_id=rec_id,
            decided_by=user.user_id,
            verdict=verdict,
            reason=reason,
            decided_at=decided_at,
        )
    )
    row.status = verdict

    policy_version_id: str | None = None
    if verdict is RecommendationStatus.APPROVED:
        agent = db.get(Agent, row.agent_id)
        policy_version_id = f"pv-{uuid.uuid4().hex[:12]}"
        apply_policy_version(
            db,
            agent,
            id=policy_version_id,
            limit=row.proposed_limit,
            rung=rung_of(row.proposed_limit),
            effective_from=decided_at,
            created_by=user.user_id,
            reason=reason,
        )

    append_entry(
        db,
        id=f"log-{uuid.uuid4().hex[:12]}",
        ts=decided_at,
        actor=user.user_id,
        actor_type="user",
        event_type="recommendation.approved" if policy_version_id else "recommendation.rejected",
        entity_type="recommendation",
        entity_id=rec_id,
        payload={
            "agent_id": row.agent_id,
            "verdict": verdict.value,
            "reason": reason,
            "proposed_limit": row.proposed_limit,
            "policy_version_id": policy_version_id,
        },
    )

    return recommendation_out(row)


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
def approve_recommendation(
    rec_id: str, body: RecommendationDecision, user: CurrentUserDep, db: DbSessionDep
) -> RecommendationOut:
    """Authorize a pending recommendation. ADMIN only.

    Writes an `approvals` row (`decided_by`, `verdict=APPROVED`, `reason`,
    `decided_at`), flips `Recommendation.status` to `APPROVED`, and — in the
    same transaction — writes the new `policy_versions` row that actually
    changes `agents.current_limit`/`current_rung`
    (docs/lanes/vp.md: "Never update agents.current_limit without writing a
    policy_versions row in the same transaction").
    """
    return _record_decision(db, user, rec_id, RecommendationStatus.APPROVED, body.reason)


@router.post(
    "/{rec_id}/reject",
    response_model=RecommendationOut,
    dependencies=[_admin_only],
    responses=_mutation_responses,
)
def reject_recommendation(
    rec_id: str, body: RecommendationDecision, user: CurrentUserDep, db: DbSessionDep
) -> RecommendationOut:
    """Reject a pending recommendation. ADMIN only, same as approve.

    Writes an `approvals` row with `verdict=REJECTED` and flips
    `Recommendation.status` to `REJECTED`. No policy version is written —
    the agent's limit does not change.
    """
    return _record_decision(db, user, rec_id, RecommendationStatus.REJECTED, body.reason)
