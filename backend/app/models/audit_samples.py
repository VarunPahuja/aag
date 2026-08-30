"""`audit_samples` — docs/lanes/vp.md schema: id, decision_id, agent_id,
sampled_at, reviewed_at, reviewer, verdict, reviewer_action.

Mirrors `shared.contracts.AuditSample` field-for-field (see that dataclass's
docstring, ADR-0009: rung-scaled post-hoc review, the ground-truth source once
the system runs past the simulator). `reviewer` is nullable and not a foreign
key to `users.id` for the same reason a sample can exist unreviewed at all:
`sampled_at` is set the moment a decision is pulled for review, before any
reviewer has looked at it.
"""

from __future__ import annotations

from datetime import datetime

from shared.enums import Action, ReviewVerdict
from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.types import enum_column


class AuditSample(Base):
    __tablename__ = "audit_samples"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    decision_id: Mapped[str] = mapped_column(ForeignKey("decisions.id"), nullable=False)
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id"), nullable=False)
    sampled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewer: Mapped[str | None] = mapped_column(String, nullable=True)
    verdict: Mapped[ReviewVerdict | None] = mapped_column(enum_column(ReviewVerdict), nullable=True)
    reviewer_action: Mapped[Action | None] = mapped_column(enum_column(Action), nullable=True)
