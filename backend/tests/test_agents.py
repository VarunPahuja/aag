from __future__ import annotations

from datetime import UTC, datetime

from shared.constants import AUTONOMY_LADDER
from shared.enums import Action, AgentState
from sqlalchemy.orm import Session

from app.models import Agent, Decision, Invoice, apply_policy_version
from app.models import TrustEvaluation as TrustEvaluationRow


def test_list_agents(client, admin_headers):
    resp = client.get("/api/v1/agents", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert {"items", "total", "page", "page_size"} <= body.keys()
    assert body["total"] == 3
    ids = {a["id"] for a in body["items"]}
    assert ids == {"agent-01", "agent-02", "agent-03"}
    for agent in body["items"]:
        assert agent["current_limit"] in AUTONOMY_LADDER


def test_get_agent(client, admin_headers):
    resp = client.get("/api/v1/agents/agent-01", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == "agent-01"
    assert body["context"]["current_limit"] == body["current_limit"]


def test_get_agent_not_found(client, admin_headers):
    resp = client.get("/api/v1/agents/does-not-exist", headers=admin_headers)
    assert resp.status_code == 404
    body = resp.json()
    assert body["code"] == "agent_not_found"
    assert "does-not-exist" in body["message"]


def test_list_policy_versions(client, admin_headers):
    resp = client.get("/api/v1/agents/agent-01/policy-versions", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3
    # newest first, and every non-first version chains to a real prior id
    ids = {v["id"] for v in body["items"]}
    for version in body["items"]:
        if version["previous_version_id"] is not None:
            assert version["previous_version_id"] in ids


def test_list_policy_versions_unknown_agent_404s(client, admin_headers):
    resp = client.get("/api/v1/agents/does-not-exist/policy-versions", headers=admin_headers)
    assert resp.status_code == 404


def test_get_current_trust(client, admin_headers):
    # agent-01 is seeded with only 3 real decisions (dec-agent01-0148..0150) —
    # nowhere near enough sample to clear the ladder's increase gates, unlike
    # app/fixtures/trust.py's 150-decision fixture. Real evidence, real
    # (smaller) numbers: this is the point of wiring the real engine in.
    resp = client.get("/api/v1/agents/agent-01/trust", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["agent_id"] == "agent-01"
    assert body["total_decisions"] == 3
    assert "id" in body  # backend-minted, not on the shared dataclass


def test_get_current_trust_persists_a_row(client, admin_headers, db_engine):
    with Session(db_engine) as session:
        before = session.query(TrustEvaluationRow).filter_by(agent_id="agent-01").count()

    resp = client.get("/api/v1/agents/agent-01/trust", headers=admin_headers)
    assert resp.status_code == 200
    row_id = resp.json()["id"]

    with Session(db_engine) as session:
        after = session.query(TrustEvaluationRow).filter_by(agent_id="agent-01").count()
        assert after == before + 1
        row = session.get(TrustEvaluationRow, row_id)
        assert row is not None
        assert row.payload["agent_id"] == "agent-01"


def test_trust_evaluation_moves_with_real_decisions(client, admin_headers, db_engine):
    """The evaluation's numbers derive from persisted decisions, not
    fixtures: add decisions for a fresh agent, re-evaluate, and the numbers
    move between the two calls."""
    with Session(db_engine) as session:
        agent = Agent(
            id="agent-moves",
            name="Moves With Decisions",
            current_limit=500,
            current_rung=0,
            state=AgentState.PROBATION,
            created_at=datetime(2026, 8, 1, tzinfo=UTC),
        )
        session.add(agent)
        apply_policy_version(
            session,
            agent,
            id="pv-agent-moves-001",
            limit=500,
            rung=0,
            effective_from=datetime(2026, 8, 1, tzinfo=UTC),
            created_by="system",
            reason="Agent onboarded at the autonomy floor.",
        )
        session.commit()

    first = client.get("/api/v1/agents/agent-moves/trust", headers=admin_headers)
    assert first.status_code == 200
    assert first.json()["total_decisions"] == 0

    with Session(db_engine) as session:
        session.add(
            Invoice(
                id="inv-moves-001",
                amount=100,
                vendor="Acme",
                category="procurement",
                submitted_at=datetime(2026, 8, 2, tzinfo=UTC),
                ground_truth_action=Action.APPROVE,
            )
        )
        session.add(
            Decision(
                id="dec-moves-001",
                sequence=1,
                invoice_id="inv-moves-001",
                agent_id="agent-moves",
                action=Action.APPROVE,
                policy_version_id="pv-agent-moves-001",
                within_limit=True,
                decided_at=datetime(2026, 8, 2, tzinfo=UTC),
            )
        )
        session.commit()

    second = client.get("/api/v1/agents/agent-moves/trust", headers=admin_headers)
    assert second.status_code == 200
    assert second.json()["total_decisions"] == 1
    assert second.json()["total_decisions"] != first.json()["total_decisions"]


def test_get_current_trust_zero_decision_agent_is_not_a_500(client, admin_headers, db_engine):
    with Session(db_engine) as session:
        session.add(
            Agent(
                id="agent-empty",
                name="No Decisions Yet",
                current_limit=500,
                current_rung=0,
                state=AgentState.PROBATION,
                created_at=datetime(2026, 8, 1, tzinfo=UTC),
            )
        )
        session.commit()

    resp = client.get("/api/v1/agents/agent-empty/trust", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["agent_id"] == "agent-empty"  # not the trust engine's "unknown"
    assert body["total_decisions"] == 0
    assert body["direction"] == "HOLD"


def test_get_current_trust_unknown_agent_404s(client, admin_headers):
    resp = client.get("/api/v1/agents/does-not-exist/trust", headers=admin_headers)
    assert resp.status_code == 404


def test_list_trust_history(client, admin_headers):
    # Seed writes one row for agent-03; each GET below adds one more.
    resp = client.get("/api/v1/agents/agent-03/trust", headers=admin_headers)
    assert resp.status_code == 200

    resp = client.get("/api/v1/agents/agent-03/trust/history", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    # newest first
    timestamps = [item["evaluated_at"] for item in body["items"]]
    assert timestamps == sorted(timestamps, reverse=True)
