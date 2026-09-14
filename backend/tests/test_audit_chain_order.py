"""The audit chain must be verified in the order it was written.

`append_entry` chains each row against the previous row by `log_seq`, and
migration 0003 added that column for exactly one reason: `ts` is supplied by
the caller and is not guaranteed monotonic with true insertion order. The
verification endpoint still read the table in `ts` order, so a perfectly
intact chain could be handed to `verify_chain` out of sequence and reported as
tampered.

Seen live, and it is the worst shape a bug can take in an audit feature: 2,912
real entries, 11 ordering inversions, chain_valid False, and the dashboard
telling a reader "tampering detected - investigate immediately" about a chain
that was never touched. A false alarm here is worse than no alarm, because it
trains people to disbelieve the one control that is supposed to be
unfalsifiable.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLogEntry, append_entry


def _append(session: Session, n: int, ts: datetime) -> None:
    append_entry(
        session,
        id=f"log-order-{n:04d}",
        ts=ts,
        actor="test",
        actor_type="system",
        event_type="test.ordering",
        entity_type="agent",
        entity_id="agent-01",
        payload={"n": n},
    )


def test_a_chain_written_with_out_of_order_timestamps_still_verifies(
    client, admin_headers, db_engine
):
    """The regression. Timestamps deliberately run backwards; insertion order
    does not. The chain is intact by construction -- `append_entry` built it --
    so the endpoint must say so."""
    base = datetime.now(UTC)
    with Session(db_engine) as session:
        # Each row is appended after the last, but carries an *earlier* ts.
        for n in range(6):
            _append(session, n, base - timedelta(minutes=n))
        session.commit()

    body = client.get("/api/v1/audit-log?page_size=1", headers=admin_headers).json()
    assert body["chain_valid"] is True, (
        "an intact chain written with non-monotonic timestamps must still verify"
    )
    assert body["chain_verified_scope"] == "full"


def test_identical_timestamps_do_not_break_verification(
    client, admin_headers, db_engine
):
    """A simulation run writes many entries inside the same second. Ordering by
    `ts` leaves their relative order undefined, which is enough to break the
    chain read even though nothing is wrong with it."""
    same = datetime.now(UTC)
    with Session(db_engine) as session:
        for n in range(10, 20):
            _append(session, n, same)
        session.commit()

    body = client.get("/api/v1/audit-log?page_size=1", headers=admin_headers).json()
    assert body["chain_valid"] is True


def test_verification_reads_in_log_seq_order(client, admin_headers, db_engine):
    """Pins the mechanism, not just the symptom. If someone re-orders this
    query by `ts` again, the two tests above might still pass by luck on a
    small fixture; this one states the requirement directly."""
    base = datetime.now(UTC)
    with Session(db_engine) as session:
        for n in range(20, 26):
            _append(session, n, base - timedelta(seconds=n))
        session.commit()

    with Session(db_engine) as session:
        by_seq = [
            r.log_seq
            for r in session.execute(
                select(AuditLogEntry).order_by(AuditLogEntry.log_seq)
            ).scalars()
        ]
        by_ts = [
            r.log_seq
            for r in session.execute(
                select(AuditLogEntry).order_by(AuditLogEntry.ts)
            ).scalars()
        ]

    assert by_seq == sorted(by_seq), "log_seq must be dense and increasing"
    assert by_ts != by_seq, (
        "precondition: this fixture must actually put ts order out of step with "
        "insertion order, or the test proves nothing"
    )
    assert client.get(
        "/api/v1/audit-log?page_size=1", headers=admin_headers
    ).json()["chain_valid"] is True


def test_real_tampering_is_still_detected(client, admin_headers, db_engine):
    """The fix must not have made verification permissive. Change one stored
    payload and the chain has to fail -- otherwise the control is decorative."""
    with Session(db_engine) as session:
        for n in range(30, 34):
            _append(session, n, datetime.now(UTC))
        session.commit()

    assert client.get(
        "/api/v1/audit-log?page_size=1", headers=admin_headers
    ).json()["chain_valid"] is True

    # Tamper directly, bypassing the ORM guard that would refuse this.
    with db_engine.begin() as conn:
        from sqlalchemy import text

        conn.execute(
            text("UPDATE audit_log SET payload = :p WHERE id = :i"),
            {"p": '{"n": 999}', "i": "log-order-0031"},
        )

    assert client.get(
        "/api/v1/audit-log?page_size=1", headers=admin_headers
    ).json()["chain_valid"] is False, "a modified payload must break the chain"
