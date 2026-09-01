"""`recommendations` — docs/lanes/vp.md schema: id, agent_id,
trust_evaluation_id, direction, proposed_limit, rationale, agent_opinions
(JSONB), status, clamped, clamped_from, generated_at.

`agent_opinions` stores the full panel — every `shared.contracts.AgentOpinion`
governance produced — as JSONB, for the same reason `trust_evaluations.payload`
does (ADR-0013): it is evidence, always read back whole, not queried field by
field. `clamped`/`clamped_from` are `app.policy.ceiling.clamp_recommendation`'s
own output, persisted rather than recomputed — see that module for why the
fact of clamping is never allowed to go unrecorded. `generated_at` mirrors
`shared.contracts.Recommendation.generated_at` and `RecommendationOut`
(`app/schemas/governance.py`) — PR #17 flagged that `openapi.json` declared
it while the table had no such column.

`governance_mode` mirrors `shared.contracts.Recommendation.governance_mode`
the same way — `RecommendationOut` (and `governance/INTEGRATION.md`) requires
it, and no column carried it until `vp/trust-governance-wiring` wired
`POST /agents/{id}/recommendations` and found the same kind of gap PR #17/#18
found for `generated_at`. `has_dissent`/`confidence`/`proposed_rung` are
deliberately NOT columns — they are derived from `agent_opinions` at read
time (`app/services/governance.py:recommendation_out`), the same reasoning
ADR-0013 gives for not normalising `trust_evaluations.payload`: redundant
storage can silently disagree with the evidence it was derived from.
"""

from __future__ import annotations

from datetime import datetime

from shared.enums import Direction, RecommendationStatus
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
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
    governance_mode: Mapped[str] = mapped_column(String, nullable=False)
    clamped: Mapped[bool] = mapped_column(Boolean, nullable=False)
    clamped_from: Mapped[int | None] = mapped_column(Integer, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
