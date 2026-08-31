"""`decisions` — docs/lanes/vp.md schema: id, sequence, invoice_id, agent_id,
action, recommended_action, human_ruling, policy_version_id, within_limit,
decided_at.

`policy_version_id` is not nullable: this is what makes "what was this agent
allowed to do at 14:00 on 3 September" answerable exactly
(docs/lanes/vp.md) — every decision references the exact append-only
`policy_versions` row in force when it was made. `within_limit` is recorded
verbatim from `app.policy.types.PolicyDecision.within_limit`
(`backend/app/policy/engine.py`) at ingest time; this table does not
recompute it.
"""

from __future__ import annotations

from datetime import datetime

from shared.enums import Action
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.types import enum_column


class Decision(Base):
    __tablename__ = "decisions"
    __table_args__ = (
        # A given agent's decisions are numbered densely from 1 — this is what
        # "the next sequence number for the agent" (backend/openapi.json,
        # POST /api/v1/decisions description) means concretely.
        UniqueConstraint("agent_id", "sequence", name="uq_decisions_agent_sequence"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    invoice_id: Mapped[str] = mapped_column(ForeignKey("invoices.id"), nullable=False)
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id"), nullable=False)
    action: Mapped[Action] = mapped_column(enum_column(Action), nullable=False)
    recommended_action: Mapped[Action | None] = mapped_column(enum_column(Action), nullable=True)
    human_ruling: Mapped[Action | None] = mapped_column(enum_column(Action), nullable=True)
    policy_version_id: Mapped[str] = mapped_column(ForeignKey("policy_versions.id"), nullable=False)
    within_limit: Mapped[bool] = mapped_column(Boolean, nullable=False)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
