"""`agents` — docs/lanes/vp.md schema: id, name, current_limit, current_rung,
state, created_at.

The `ck_agents_rung_matches_limit` check constraint enforces, at the database
level and for every write path (ORM, raw SQL, a future admin script), the
invariant `shared.contracts.TrustEvaluation`'s own docstring states:
`rung_of(current_limit) == current_rung` must always hold. It is generated
from `shared.constants.AUTONOMY_LADDER` rather than hand-written, so the five
allowed pairs can never drift from the ladder itself.

That constraint alone does not stop `agents.current_limit` from being updated
without a `policy_versions` row in the same transaction — a mismatched
(limit, rung) pair is rejected, but a *consistent* pair written without a
paired version row is not. `app/models/guards.py` closes that gap with a
`before_flush` session hook; `apply_policy_version` below is the one
sanctioned way to change both together correctly.
"""

from __future__ import annotations

from datetime import datetime

from shared.constants import AUTONOMY_LADDER
from shared.enums import AgentState
from sqlalchemy import CheckConstraint, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.types import enum_column

_RUNG_MATCHES_LIMIT_SQL = " OR ".join(
    f"(current_limit = {limit} AND current_rung = {rung})"
    for rung, limit in enumerate(AUTONOMY_LADDER)
)


class Agent(Base):
    __tablename__ = "agents"
    __table_args__ = (
        CheckConstraint(_RUNG_MATCHES_LIMIT_SQL, name="ck_agents_rung_matches_limit"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    current_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    current_rung: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[AgentState] = mapped_column(enum_column(AgentState), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
