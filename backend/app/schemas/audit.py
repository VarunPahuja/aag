"""Audit-sample and audit-log response models.

`AuditSampleOut` mirrors `shared.contracts.AuditSample` field-for-field.
`AuditLogEntryOut` has no `shared/` equivalent — it's a backend-local
resource (docs/lanes/vp.md's `audit_log` table: hash-chained, append-only).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from shared.enums import Action, ReviewVerdict


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
