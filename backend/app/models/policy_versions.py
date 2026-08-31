"""`policy_versions` — docs/lanes/vp.md schema: id, agent_id, limit, rung,
effective_from, created_by, reason, previous_version_id.

Append-only: no update path anywhere in this codebase, enforced at the ORM
session level by `app/models/guards.py` (a `before_flush` hook raises
`ImmutableRowError` on any attempt to modify or delete an existing row).
`previous_version_id` chains each row to the one it replaced — `None` only on
an agent's very first version — so the full history of what an agent was
allowed to do is reconstructable at any point in time, never overwritten.

`apply_policy_version` is the one sanctioned way to change
`agents.current_limit`/`current_rung`: it writes the new version row and
updates the agent in the same flush, and validates `rung_of(limit) == rung`
before doing either. `app/models/guards.py` backs this up independently —
changing `Agent.current_limit`/`current_rung` any other way, without a new
`PolicyVersion` in the same flush, raises before the flush commits.
"""

from __future__ import annotations

from datetime import datetime

from shared.constants import rung_of
from sqlalchemy import DateTime, ForeignKey, Integer, String, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.models.agents import Agent
from app.models.base import Base


class PolicyVersion(Base):
    __tablename__ = "policy_versions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id"), nullable=False)
    limit: Mapped[int] = mapped_column(Integer, nullable=False)
    rung: Mapped[int] = mapped_column(Integer, nullable=False)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # Not a foreign key to users.id: the system itself authors a version
    # (automatic clawback, initial onboarding) and is recorded as the literal
    # string "system" (see app/fixtures/policy_versions.py), which is not a
    # persisted user row and never will be.
    created_by: Mapped[str] = mapped_column(String, nullable=False)
    reason: Mapped[str] = mapped_column(String, nullable=False)
    previous_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("policy_versions.id"), nullable=True
    )


def current_policy_version_for(session: Session, agent_id: str) -> PolicyVersion | None:
    """The policy version currently in force for `agent_id` — the one with
    the latest `effective_from`. `None` if the agent has no policy version on
    record at all: shouldn't happen for a properly onboarded agent (every
    agent gets an initial version via `apply_policy_version` at creation —
    see `app/seed.py`), but the decision-ingest path must not assume it."""
    return (
        session.execute(
            select(PolicyVersion)
            .where(PolicyVersion.agent_id == agent_id)
            .order_by(PolicyVersion.effective_from.desc())
        )
        .scalars()
        .first()
    )


def apply_policy_version(
    session: Session,
    agent: Agent,
    *,
    id: str,
    limit: int,
    rung: int,
    effective_from: datetime,
    created_by: str,
    reason: str,
) -> PolicyVersion:
    """Change `agent`'s limit the one correct way: a new append-only
    `PolicyVersion` row, chained to whatever was previously in force for this
    agent, plus the matching update to `agent.current_limit`/`current_rung` —
    added to `session` together so they commit in the same transaction.

    Raises `ValueError` before touching `session` at all if `limit`/`rung`
    don't agree with `shared.constants.rung_of` — the same invariant
    `ck_agents_rung_matches_limit` (`app/models/agents.py`) enforces at the
    database level, checked here too so the caller gets a clear message
    instead of an `IntegrityError` from a constraint it never saw.
    """
    if rung_of(limit) != rung:
        raise ValueError(
            f"limit {limit} corresponds to rung {rung_of(limit)} (shared.constants.rung_of), "
            f"not rung {rung} — refusing to write an inconsistent policy version."
        )

    previous = (
        session.execute(
            select(PolicyVersion)
            .where(PolicyVersion.agent_id == agent.id)
            .order_by(PolicyVersion.effective_from.desc())
        )
        .scalars()
        .first()
    )

    version = PolicyVersion(
        id=id,
        agent_id=agent.id,
        limit=limit,
        rung=rung,
        effective_from=effective_from,
        created_by=created_by,
        reason=reason,
        previous_version_id=previous.id if previous is not None else None,
    )
    agent.current_limit = limit
    agent.current_rung = rung
    session.add(version)
    return version
