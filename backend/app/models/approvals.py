"""`approvals` — docs/lanes/vp.md schema: id, recommendation_id, decided_by,
verdict, reason, decided_at.

`verdict` reuses `shared.enums.RecommendationStatus` rather than inventing a
new two-value enum: a human approval's outcome is exactly the
`APPROVED`/`REJECTED` half of that enum's already-shared vocabulary
(`RecommendationOut.status` takes the same two values on this path — see
`backend/openapi.json`'s `approve`/`reject` endpoints). `PENDING` and
`SUPERSEDED` describe a recommendation's lifecycle before or after a human
acts, never the human's own verdict, so the check constraint below excludes
them here — reusing the enum's storage and serialisation without also
accepting values this column can never legitimately hold.
"""

from __future__ import annotations

from datetime import datetime

from shared.enums import RecommendationStatus
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.types import enum_column


class Approval(Base):
    __tablename__ = "approvals"
    __table_args__ = (
        CheckConstraint(
            "verdict IN ('APPROVED', 'REJECTED')", name="ck_approvals_verdict_is_a_human_verdict"
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    recommendation_id: Mapped[str] = mapped_column(ForeignKey("recommendations.id"), nullable=False)
    decided_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    verdict: Mapped[RecommendationStatus] = mapped_column(
        enum_column(RecommendationStatus), nullable=False
    )
    reason: Mapped[str] = mapped_column(String, nullable=False)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
