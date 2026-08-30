"""`trust_evaluations` — docs/lanes/vp.md schema: id, agent_id, evaluated_at,
trust_score, recommended_limit, direction, payload (JSONB).

`payload` holds the complete `shared.contracts.TrustEvaluation` — every
`ProportionResult`, `ScoreComponent`, `DriftResult`, and reason code — as one
JSONB blob. See ADR-0013 for why this is stored whole rather than normalised
into its own tables: it is an evidence snapshot, always read back whole, never
queried by its internal fields. The four scalar columns alongside it
(`trust_score`, `recommended_limit`, `direction`, plus `evaluated_at`) are the
fields a listing or a chart actually filters/sorts/aggregates by — pulled out
so those operations don't require unpacking JSON in every query.
"""

from __future__ import annotations

from datetime import datetime

from shared.enums import Direction
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.types import JSONBType, enum_column


class TrustEvaluation(Base):
    __tablename__ = "trust_evaluations"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id"), nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    trust_score: Mapped[float] = mapped_column(Float, nullable=False)
    recommended_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    direction: Mapped[Direction] = mapped_column(enum_column(Direction), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONBType, nullable=False)
