"""Decision fixtures — built as real `shared.contracts.DecisionRecord`
instances (see `app/fixtures/trust.py` for why: a shape mismatch fails at
import time, not silently in a response).

A representative sample per agent, not the full history the aggregate
counts on their `TrustEvaluation`s imply — this is fixture data for
`GET /decisions` and `GET /decisions/{id}`, not a literal backing store.
`agent-03`'s decision list includes the critical error
(`APPROVE` where `ground_truth` is `REJECT`) that contributed to the
confirmed-drift clawback in `app/fixtures/trust.py`.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from shared.contracts import DecisionRecord
from shared.enums import Action

from app.schemas.decision import DecisionRecordOut

_NOW = datetime(2026, 8, 27, 12, 0, tzinfo=UTC)

_RECORDS: list[DecisionRecord] = [
    # agent-01 — clean run, one escalation with a human ruling
    DecisionRecord(
        decision_id="dec-agent01-0148", sequence=148, invoice_id="inv-1148",
        amount=1800, action=Action.APPROVE, ground_truth=Action.APPROVE,
        agent_id="agent-01", decided_at=_NOW - timedelta(hours=3),
    ),
    DecisionRecord(
        decision_id="dec-agent01-0149", sequence=149, invoice_id="inv-1149",
        amount=2400, action=Action.ESCALATE, ground_truth=Action.APPROVE,
        agent_id="agent-01", decided_at=_NOW - timedelta(hours=2),
        recommended_action=Action.APPROVE, human_ruling=Action.APPROVE,
    ),
    DecisionRecord(
        decision_id="dec-agent01-0150", sequence=150, invoice_id="inv-1150",
        amount=900, action=Action.REJECT, ground_truth=Action.REJECT,
        agent_id="agent-01", decided_at=_NOW - timedelta(hours=1),
    ),
    # agent-02 — small sample, still on probation
    DecisionRecord(
        decision_id="dec-agent02-0012", sequence=12, invoice_id="inv-2012",
        amount=420, action=Action.APPROVE, ground_truth=Action.APPROVE,
        agent_id="agent-02", decided_at=_NOW - timedelta(hours=5),
    ),
    DecisionRecord(
        decision_id="dec-agent02-0013", sequence=13, invoice_id="inv-2013",
        amount=480, action=Action.ESCALATE, ground_truth=Action.REJECT,
        agent_id="agent-02", decided_at=_NOW - timedelta(hours=4),
        recommended_action=Action.REJECT, human_ruling=Action.REJECT,
    ),
    # agent-03 — includes the critical error behind the confirmed-drift clawback
    DecisionRecord(
        decision_id="dec-agent03-0193", sequence=193, invoice_id="inv-3193",
        amount=2200, action=Action.APPROVE, ground_truth=Action.REJECT,  # critical error
        agent_id="agent-03", decided_at=_NOW - timedelta(days=2, hours=1),
    ),
    DecisionRecord(
        decision_id="dec-agent03-0194", sequence=194, invoice_id="inv-3194",
        amount=950, action=Action.APPROVE, ground_truth=Action.APPROVE,
        agent_id="agent-03", decided_at=_NOW - timedelta(days=2),
    ),
    DecisionRecord(
        decision_id="dec-agent03-0195", sequence=195, invoice_id="inv-3195",
        amount=700, action=Action.APPROVE, ground_truth=Action.APPROVE,
        agent_id="agent-03", decided_at=_NOW - timedelta(hours=6),
    ),
]

DECISIONS: list[DecisionRecordOut] = [
    DecisionRecordOut.model_validate(record, from_attributes=True) for record in _RECORDS
]

DECISIONS_BY_ID: dict[str, DecisionRecordOut] = {d.decision_id: d for d in DECISIONS}
