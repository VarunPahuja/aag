"""`recommendations` — docs/lanes/vp.md schema: id, agent_id,
trust_evaluation_id, direction, proposed_limit, rationale, agent_opinions
(JSONB), status, clamped, clamped_from.

`agent_opinions` stores the full panel — every `shared.contracts.AgentOpinion`
governance produced — as JSONB, for the same reason `trust_evaluations.payload`
does (ADR-0013): it is evidence, always read back whole, not queried field by
field. `clamped`/`clamped_from` are `app.policy.ceiling.clamp_recommendation`'s
own output, persisted rather than recomputed — see that module for why the
fact of clamping is never allowed to go unrecorded.
"""

from __future__ import annotations

from shared.enums import Direction, RecommendationStatus
from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.types import JSONBType, enum_column


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id"), nullable=False)
    trust_evaluation_id: Mapped[str] = mapped_column(
        ForeignKey("trust_evaluations.id"), nullable=False
    )
    direction: Mapped[Direction] = mapped_column(enum_column(Direction), nullable=False)
    proposed_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    rationale: Mapped[str] = mapped_column(String, nullable=False)
    agent_opinions: Mapped[list] = mapped_column(JSONBType, nullable=False)
    status: Mapped[RecommendationStatus] = mapped_column(
        enum_column(RecommendationStatus), nullable=False
    )
    clamped: Mapped[bool] = mapped_column(Boolean, nullable=False)
    clamped_from: Mapped[int | None] = mapped_column(Integer, nullable=True)
