from __future__ import annotations

import pytest
from shared.contracts import Recommendation
from shared.enums import Direction, RecommendationStatus
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Agent, AuditLogEntry
from app.models import Recommendation as RecommendationRow
from app.models import TrustEvaluation as TrustEvaluationRow
from app.models.audit_hash import GENESIS_HASH, compute_hash
from app.services.governance import generate_recommendation


def test_list_recommendations(client, admin_headers):
    # seed.py persists three rows: rec-agent01-001 (PENDING), rec-agent03-001
    # (APPROVED clawback), rec-agent01-000 (APPROVED, an earlier increase) —
    # one more than app/fixtures/recommendations.py's two, which never
    # included the historical rec-agent01-000.
    resp = client.get("/api/v1/recommendations", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3
    directions = {r["direction"] for r in body["items"]}
    assert directions == {"INCREASE", "CLAWBACK"}


def test_get_recommendation(client, admin_headers):
    resp = client.get("/api/v1/recommendations/rec-agent01-001", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["direction"] == "INCREASE"
    assert len(body["opinions"]) == 4
    # the hard ceiling, visible in the response, not just in a log
    assert body["clamped"] is True
    assert body["clamped_from"] == 10000


def test_get_recommendation_not_found(client, admin_headers):
    resp = client.get("/api/v1/recommendations/does-not-exist", headers=admin_headers)
    assert resp.status_code == 404


def test_approve_recommendation_as_admin(client, admin_headers):
    resp = client.post(
        "/api/v1/recommendations/rec-agent01-001/approve",
        headers=admin_headers,
        json={"reason": "Evidence is solid, cooldown satisfied."},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "APPROVED"


def test_approve_recommendation_requires_reason(client, admin_headers):
    resp = client.post(
        "/api/v1/recommendations/rec-agent01-001/approve", headers=admin_headers, json={}
    )
    assert resp.status_code == 422


def test_reviewer_cannot_approve(client, reviewer_headers):
    # docs/lanes/vp.md, Thu 10 Sept security-pass check: "Reviewer cannot approve"
    resp = client.post(
        "/api/v1/recommendations/rec-agent01-001/approve",
        headers=reviewer_headers,
        json={"reason": "trying anyway"},
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "forbidden"


def test_auditor_cannot_approve(client, auditor_headers):
    resp = client.post(
        "/api/v1/recommendations/rec-agent01-001/approve",
        headers=auditor_headers,
        json={"reason": "trying anyway"},
    )
    assert resp.status_code == 403


def test_reject_recommendation_as_admin(client, admin_headers):
    resp = client.post(
        "/api/v1/recommendations/rec-agent01-001/reject",
        headers=admin_headers,
        json={"reason": "Not this time."},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "REJECTED"


def test_cannot_decide_an_already_resolved_recommendation(client, admin_headers):
    # rec-agent03-001 is already APPROVED (an automatic clawback) in the fixture.
    resp = client.post(
        "/api/v1/recommendations/rec-agent03-001/approve",
        headers=admin_headers,
        json={"reason": "trying anyway"},
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "recommendation_already_resolved"


# --- generation: POST /agents/{agent_id}/recommendations --------------------------------


def test_generate_recommendation_persists_a_row(client, admin_headers, db_engine):
    resp = client.post("/api/v1/agents/agent-01/recommendations", headers=admin_headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["agent_id"] == "agent-01"
    assert body["status"] == "PENDING"  # governance can never self-approve, ADR-0004
    assert len(body["opinions"]) == 4

    with Session(db_engine) as session:
        row = session.get(RecommendationRow, body["recommendation_id"])
        assert row is not None
        assert len(row.agent_opinions) == 4
        assert row.trust_evaluation_id is not None
        assert session.get(TrustEvaluationRow, row.trust_evaluation_id) is not None


def test_generate_recommendation_unknown_agent_404s(client, admin_headers):
    resp = client.post("/api/v1/agents/does-not-exist/recommendations", headers=admin_headers)
    assert resp.status_code == 404


def test_recommendation_above_evidence_is_clamped(client, admin_headers, monkeypatch):
    """Governance's own `_aggregate` already asserts it can never propose
    above `evaluation.recommended_limit` (governance/governance/coordinator.py,
    governance/INTEGRATION.md) — this proves the *backend's* independent
    clamp still fires and is recorded, the way it would have to if that
    assertion were ever wrong. Only `recommend()`'s return value is faked;
    `clamp_recommendation` runs for real, exactly as it would against a live
    proposal (docs/lanes/vp.md, responsibility 4 — the architectural claim)."""

    def _rigged_recommend(evaluation, mode=None, trust_evaluation_ref=None):
        return Recommendation(
            recommendation_id="rigged",
            agent_id=evaluation.agent_id,
            direction=Direction.INCREASE,
            proposed_limit=999_999,  # absurdly above evaluation.recommended_limit
            proposed_rung=4,
            rationale="rigged for the clamp test",
            opinions=(),
            has_dissent=False,
            confidence=1.0,
            governance_mode="stub",
            status=RecommendationStatus.PENDING,
            trust_evaluation_ref=trust_evaluation_ref,
            generated_at=None,
            clamped=False,
            clamped_from=None,
        )

    monkeypatch.setattr("app.services.governance.recommend", _rigged_recommend)

    resp = client.post("/api/v1/agents/agent-01/recommendations", headers=admin_headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["clamped"] is True
    assert body["clamped_from"] == 999_999
    assert body["proposed_limit"] < 999_999


def test_every_generation_appends_exactly_one_audit_entry_and_the_chain_verifies(
    client, admin_headers, db_engine
):
    with Session(db_engine) as session:
        before = session.query(AuditLogEntry).count()

    for _ in range(3):
        resp = client.post("/api/v1/agents/agent-01/recommendations", headers=admin_headers)
        assert resp.status_code == 201

    with Session(db_engine) as session:
        after = session.query(AuditLogEntry).count()
        generated = (
            session.query(AuditLogEntry)
            .filter(AuditLogEntry.event_type == "recommendation.generated")
            .count()
        )
        assert after - before == 3
        assert generated == 3

        entries = session.query(AuditLogEntry).order_by(AuditLogEntry.ts).all()
        prev_hash = GENESIS_HASH
        for entry in entries:
            assert entry.prev_hash == prev_hash
            assert entry.hash == compute_hash(prev_hash, entry.payload)
            prev_hash = entry.hash


def test_cached_mode_with_no_matching_recording_returns_503_not_500(
    client, admin_headers, monkeypatch
):
    # agent-01's real, DB-derived evidence does not match any of the
    # committed demo-scenario recordings (governance/recordings/) — cached
    # mode has to miss, cleanly, for evidence nobody recorded a response to.
    monkeypatch.setenv("GOVERNANCE_MODE", "cached")
    resp = client.post("/api/v1/agents/agent-01/recommendations", headers=admin_headers)
    assert resp.status_code == 503
    body = resp.json()
    assert body["code"] == "governance_unavailable"
    assert "agent-01" in body["message"]


def test_recommendation_generation_mid_transaction_failure_rolls_back_everything(db_engine):
    with Session(db_engine) as session:
        before_trust = session.query(TrustEvaluationRow).count()
        before_rec = session.query(RecommendationRow).count()
        before_audit = session.query(AuditLogEntry).count()

        agent = session.get(Agent, "agent-01")
        recommendation_out = generate_recommendation(session, agent)

        # Force a second, colliding row into the same, still-uncommitted
        # transaction — proves the whole transaction (trust evaluation +
        # recommendation + audit_log, all added above) is atomic, not just
        # the first insert, the same way test_decisions.py proves it for
        # decision ingest.
        session.add(
            RecommendationRow(
                id=recommendation_out.recommendation_id,
                agent_id="agent-01",
                trust_evaluation_id=recommendation_out.trust_evaluation_ref,
                direction=recommendation_out.direction,
                proposed_limit=recommendation_out.proposed_limit,
                rationale="duplicate id, forced collision",
                agent_opinions=[],
                status=recommendation_out.status,
                governance_mode=recommendation_out.governance_mode,
                clamped=False,
                clamped_from=None,
                generated_at=recommendation_out.generated_at,
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

    with Session(db_engine) as verify:
        assert verify.query(TrustEvaluationRow).count() == before_trust
        assert verify.query(RecommendationRow).count() == before_rec
        assert verify.query(AuditLogEntry).count() == before_audit
