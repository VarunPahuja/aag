"""`audit_log` — docs/lanes/vp.md schema: id, ts, actor, actor_type,
event_type, entity_type, entity_id, payload (JSONB), prev_hash, hash.

Append-only, same enforcement as `policy_versions`
(`app/models/guards.py`'s `before_flush` hook raises on any attempt to modify
or delete an existing row). `entity_type`/`entity_id` are a deliberately
untyped polymorphic reference — this table logs events against decisions,
policy versions, recommendations, audit samples, and more, and adding a real
foreign key per entity type would mean a new column and a new migration every
time a new kind of event needs logging. Verifying the chain (recomputing each
row's `hash` from `prev_hash` and its own `payload` via `app.models.audit_hash
.compute_hash`) is left as a read-side operation for whoever needs it, not
something this model does on every read.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.models.audit_hash import GENESIS_HASH, compute_hash
from app.models.base import Base
from app.models.types import JSONBType


class AuditLogEntry(Base):
    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actor: Mapped[str] = mapped_column(String, nullable=False)
    actor_type: Mapped[str] = mapped_column(String, nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    entity_type: Mapped[str] = mapped_column(String, nullable=False)
    entity_id: Mapped[str] = mapped_column(String, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONBType, nullable=False)
    prev_hash: Mapped[str] = mapped_column(String, nullable=False)
    hash: Mapped[str] = mapped_column(String, nullable=False, unique=True)


def append_entry(
    session: Session,
    *,
    id: str,
    ts: datetime,
    actor: str,
    actor_type: str,
    event_type: str,
    entity_type: str,
    entity_id: str,
    payload: dict,
) -> AuditLogEntry:
    """Append the next row of the chain, hashing it against whatever the
    latest row in `session` currently is (or `GENESIS_HASH` for the first row
    ever). A convenience for tests and the seed script — full ingest wiring
    (appending an entry as part of every mutating request) is separate work.
    """
    previous = (
        session.execute(select(AuditLogEntry).order_by(AuditLogEntry.ts.desc())).scalars().first()
    )
    prev_hash = previous.hash if previous is not None else GENESIS_HASH
    entry = AuditLogEntry(
        id=id,
        ts=ts,
        actor=actor,
        actor_type=actor_type,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        payload=payload,
        prev_hash=prev_hash,
        hash=compute_hash(prev_hash, payload),
    )
    session.add(entry)
    return entry
