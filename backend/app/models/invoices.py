"""`invoices` — docs/lanes/vp.md schema: id, amount, vendor, category,
submitted_at, ground_truth_action.

Holds the fields `shared.contracts.DecisionRecord` carries inline
(`amount`, `ground_truth`) as their own row, submitted once per invoice and
referenced by every `decisions` row that acts on it — normalised here,
unlike `trust_evaluations.payload` / `recommendations.agent_opinions`
(ADR-0013), because an invoice is a fact recorded once, not an evidence
snapshot read back whole.
"""

from __future__ import annotations

from datetime import datetime

from shared.enums import Action
from sqlalchemy import CheckConstraint, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.types import enum_column


class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_invoices_amount_positive"),
        # shared/contracts.py, DecisionRecord docstring: "Ground truth is
        # always APPROVE or REJECT, because every synthetic invoice carries a
        # deterministic correct answer." ESCALATE is only ever an agent action.
        CheckConstraint(
            "ground_truth_action IN ('APPROVE', 'REJECT')",
            name="ck_invoices_ground_truth_not_escalate",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    vendor: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ground_truth_action: Mapped[Action] = mapped_column(enum_column(Action), nullable=False)
