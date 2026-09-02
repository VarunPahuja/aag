"""Audit-sample and audit-log resources — the post-hoc review queue (ADR-0009)
and the hash-chained record of everything the system has done.

`list_audit_log` reads the real `audit_log` table (vp/approval-workflow) and
recomputes the chain fresh on every call — the tamper-evidence property
docs/lanes/vp.md claims, demonstrable, not just asserted. Audit samples
remain fixture-backed — out of scope here.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.api.v1.pagination import PageParam, PageSizeParam, paginate
from app.deps import CurrentUserDep, DbSessionDep, require_role
from app.errors import (
    CONFLICT_RESPONSE,
    FORBIDDEN_RESPONSE,
    NOT_FOUND_RESPONSE,
    ApiError,
    not_found,
)
from app.fixtures.audit import AUDIT_SAMPLES, AUDIT_SAMPLES_BY_ID
from app.models import AuditLogEntry
from app.models.audit_hash import verify_chain
from app.schemas.audit import AuditLogEntryOut, AuditLogPage, AuditSampleOut, AuditSampleReview
from app.schemas.envelope import Page
from app.schemas.user import Role

router = APIRouter(tags=["audit"])

# Reviewing a sample is REVIEWER's actual job (ADR-0009); ADMIN may also do it.
# AUDITOR stays read-only everywhere, including here.
_reviewer_or_admin = Depends(require_role(Role.ADMIN, Role.REVIEWER))


@router.get("/audit-samples", response_model=Page[AuditSampleOut])
def list_audit_samples(
    user: CurrentUserDep, page: PageParam = 1, page_size: PageSizeParam = 20
) -> Page[AuditSampleOut]:
    """List sampled decisions pulled for human review, newest first.

    Once implemented: `SELECT ... ORDER BY sampled_at DESC`, with a
    `?pending=true` filter for the review queue view — samples are pulled
    at `sampling_rate_of(agent.current_rung)` (shared/constants.py) as
    decisions are recorded, not on a schedule.
    """
    return paginate(list(reversed(AUDIT_SAMPLES)), page, page_size)


@router.post(
    "/audit-samples/{sample_id}/review",
    response_model=AuditSampleOut,
    dependencies=[_reviewer_or_admin],
    responses={**NOT_FOUND_RESPONSE, **FORBIDDEN_RESPONSE, **CONFLICT_RESPONSE},
)
def review_audit_sample(sample_id: str, body: AuditSampleReview) -> AuditSampleOut:
    """Record a human review of one sampled decision. REVIEWER or ADMIN only.

    Once implemented: writes `reviewed_at`/`reviewer`/`verdict`/
    `reviewer_action` onto the `audit_samples` row, and — if `verdict` is
    `DISAGREED` — emits `SAMPLE_REVIEW_DISAGREEMENT`
    (shared/reason_codes.py) into the agent's next trust evaluation, since
    a disagreeing sample is itself evidence. This stub validates the sample
    exists and is still pending, then returns a copy reflecting the
    review — it does not persist it or feed the trust engine.
    """
    sample = AUDIT_SAMPLES_BY_ID.get(sample_id)
    if sample is None:
        raise not_found(
            "audit_sample_not_found", f"No audit sample {sample_id!r}.", {"sample_id": sample_id}
        )
    already_reviewed = sample.reviewed_at is not None and sample.verdict is not None
    if already_reviewed:
        raise ApiError(
            status_code=409,
            code="audit_sample_already_reviewed",
            message=f"Audit sample {sample_id!r} was already reviewed.",
            detail={"sample_id": sample_id, "reviewed_at": str(sample.reviewed_at)},
        )
    return sample.model_copy(
        update={
            "reviewed_at": datetime.now(UTC),
            "reviewer": "current-reviewer",  # real identity once auth is real
            "verdict": body.verdict,
            "reviewer_action": body.reviewer_action,
        }
    )


@router.get("/audit-log", response_model=AuditLogPage)
def list_audit_log(
    db: DbSessionDep, user: CurrentUserDep, page: PageParam = 1, page_size: PageSizeParam = 20
) -> AuditLogPage:
    """The complete hash-chained event log, newest first. Read-only —
    nothing in this API ever mutates an existing row (that's the point).

    Recomputes the whole chain from `GENESIS_HASH` on every call —
    `audit_log` is small enough in this system for that to be cheap — and
    reports the result as `chain_valid`/`chain_verified_scope` rather than
    just asserting immutability in a docstring. If the table ever grows
    large enough that a full recompute stops being cheap, this falls back
    to verifying only the returned page and says so via
    `chain_verified_scope`, instead of silently verifying less than it
    claims.
    """
    rows = db.execute(select(AuditLogEntry).order_by(AuditLogEntry.ts)).scalars().all()
    chain_valid = verify_chain((row.prev_hash, row.payload, row.hash) for row in rows)

    newest_first = list(reversed(rows))
    page_result = paginate(
        [AuditLogEntryOut.model_validate(row) for row in newest_first], page, page_size
    )
    return AuditLogPage(
        items=page_result.items,
        total=page_result.total,
        page=page_result.page,
        page_size=page_result.page_size,
        chain_valid=chain_valid,
        chain_verified_scope="full",
    )
