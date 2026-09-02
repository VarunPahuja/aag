"""Audit-sample and audit-log response models.

`AuditSampleOut` mirrors `shared.contracts.AuditSample` field-for-field.
`AuditLogEntryOut` has no `shared/` equivalent — it's a backend-local
resource (docs/lanes/vp.md's `audit_log` table: hash-chained, append-only).
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from shared.enums import Action, ReviewVerdict

from app.schemas.envelope import Page


class AuditSampleOut(BaseModel):
    """Mirrors `shared.contracts.AuditSample` field-for-field."""

    model_config = ConfigDict(from_attributes=True)

    sample_id: str
    decision_id: str
    agent_id: str
    sampled_at: datetime | None
    reviewed_at: datetime | None
    reviewer: str | None
    verdict: ReviewVerdict | None
    reviewer_action: Action | None


class AuditSampleReview(BaseModel):
    """Request body for `POST /api/v1/audit-samples/{sample_id}/review`.

    Only ADMIN or REVIEWER may call this (`app/deps.py`) — reviewing sampled
    decisions is REVIEWER's actual job (ADR-0009); AUDITOR stays read-only.
    """

    verdict: ReviewVerdict
    reviewer_action: Action
    reason: str = Field(min_length=1, description="What the reviewer found, and why")


class AuditLogEntryOut(BaseModel):
    """One hash-chained row. `prev_hash`/`hash` make tampering with history
    detectable — see docs/lanes/vp.md: "sha256(prev_hash +
    canonical_json(payload))". Read-only; nothing in this API ever mutates
    an existing row.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    ts: datetime
    actor: str
    actor_type: str
    event_type: str
    entity_type: str
    entity_id: str
    payload: dict
    prev_hash: str
    hash: str


class AuditLogPage(Page[AuditLogEntryOut]):
    """`GET /api/v1/audit-log`'s response: the usual pagination envelope,
    plus a chain-verification result computed fresh on every call — this is
    what makes tamper-evidence demonstrable on screen rather than claimed in
    a docstring (docs/lanes/vp.md).

    `chain_verified_scope` says exactly what `chain_valid` covers: `"full"`
    when every row in `audit_log` was recomputed from `GENESIS_HASH`,
    `"page"` if the table ever grows large enough that a full recompute on
    every request stops being cheap and this endpoint falls back to
    verifying only the returned page — never silently verifying less than
    it claims.
    """

    chain_valid: bool
    chain_verified_scope: Literal["full", "page"]
