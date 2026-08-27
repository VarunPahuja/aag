"""Audit-sample and audit-log fixtures.

`AuditSample` rows are built as real `shared.contracts.AuditSample`
instances (see `app/fixtures/trust.py` for why). The audit-log hashes below
are computed for real, not typed out by hand — `sha256(prev_hash +
canonical_json(payload))`, chained — so this fixture already demonstrates
the tamper-evidence property docs/lanes/vp.md describes, not just its shape.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta

from shared.contracts import AuditSample
from shared.enums import Action, ReviewVerdict

from app.schemas.audit import AuditLogEntryOut, AuditSampleOut

_NOW = datetime(2026, 8, 27, 12, 0, tzinfo=UTC)

_SAMPLE_RECORDS: list[AuditSample] = [
    AuditSample(
        sample_id="sample-001", decision_id="dec-agent01-0148", agent_id="agent-01",
        sampled_at=_NOW - timedelta(hours=3), reviewed_at=_NOW - timedelta(hours=1),
        reviewer="user-reviewer-01", verdict=ReviewVerdict.AGREED, reviewer_action=Action.APPROVE,
    ),
    AuditSample(
        sample_id="sample-002", decision_id="dec-agent02-0012", agent_id="agent-02",
        sampled_at=_NOW - timedelta(hours=5), reviewed_at=None,
        reviewer=None, verdict=None, reviewer_action=None,
    ),
    AuditSample(
        sample_id="sample-003", decision_id="dec-agent03-0193", agent_id="agent-03",
        sampled_at=_NOW - timedelta(days=2, hours=1), reviewed_at=_NOW - timedelta(days=1, hours=20),
        reviewer="user-reviewer-01", verdict=ReviewVerdict.DISAGREED, reviewer_action=Action.REJECT,
    ),
    AuditSample(
        sample_id="sample-004", decision_id="dec-agent03-0195", agent_id="agent-03",
        sampled_at=_NOW - timedelta(hours=6), reviewed_at=None,
        reviewer=None, verdict=None, reviewer_action=None,
    ),
]

AUDIT_SAMPLES: list[AuditSampleOut] = [
    AuditSampleOut.model_validate(s, from_attributes=True) for s in _SAMPLE_RECORDS
]
AUDIT_SAMPLES_BY_ID: dict[str, AuditSampleOut] = {s.sample_id: s for s in AUDIT_SAMPLES}


def _hash_entry(prev_hash: str, payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256((prev_hash + canonical).encode("utf-8")).hexdigest()


_GENESIS_HASH = "0" * 64

_RAW_ENTRIES: list[dict] = [
    {
        "id": "log-0001", "ts": _NOW - timedelta(days=2, hours=1, minutes=1),
        "actor": "agent-03", "actor_type": "agent", "event_type": "decision.recorded",
        "entity_type": "decision", "entity_id": "dec-agent03-0193",
        "payload": {"action": "APPROVE", "amount": 2200},
    },
    {
        "id": "log-0002", "ts": _NOW - timedelta(days=2),
        "actor": "system", "actor_type": "system", "event_type": "trust.evaluated",
        "entity_type": "trust_evaluation", "entity_id": "trust-eval-agent03-002",
        "payload": {"trust_score": 41.2, "direction": "CLAWBACK"},
    },
    {
        "id": "log-0003", "ts": _NOW - timedelta(days=2) + timedelta(minutes=1),
        "actor": "system", "actor_type": "system", "event_type": "recommendation.applied",
        "entity_type": "recommendation", "entity_id": "rec-agent03-001",
        "payload": {"direction": "CLAWBACK", "proposed_limit": 1000, "status": "APPROVED"},
    },
    {
        "id": "log-0004", "ts": _NOW - timedelta(days=2) + timedelta(minutes=2),
        "actor": "system", "actor_type": "system", "event_type": "policy_version.created",
        "entity_type": "policy_version", "entity_id": "pv-agent03-004",
        "payload": {"agent_id": "agent-03", "limit": 1000, "rung": 1,
                     "reason": "Automatic clawback: confirmed drift."},
    },
    {
        "id": "log-0005", "ts": _NOW - timedelta(hours=1),
        "actor": "user-reviewer-01", "actor_type": "user", "event_type": "audit_sample.reviewed",
        "entity_type": "audit_sample", "entity_id": "sample-001",
        "payload": {"verdict": "AGREED", "reviewer_action": "APPROVE"},
    },
]


def _build_chain() -> list[AuditLogEntryOut]:
    chain: list[AuditLogEntryOut] = []
    prev_hash = _GENESIS_HASH
    for raw in _RAW_ENTRIES:
        entry_hash = _hash_entry(prev_hash, raw["payload"])
        chain.append(
            AuditLogEntryOut(
                id=raw["id"], ts=raw["ts"], actor=raw["actor"], actor_type=raw["actor_type"],
                event_type=raw["event_type"], entity_type=raw["entity_type"],
                entity_id=raw["entity_id"], payload=raw["payload"],
                prev_hash=prev_hash, hash=entry_hash,
            )
        )
        prev_hash = entry_hash
    return chain


AUDIT_LOG: list[AuditLogEntryOut] = _build_chain()
