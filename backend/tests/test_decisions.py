from __future__ import annotations


def test_create_decision(client, admin_headers):
    resp = client.post(
        "/api/v1/decisions",
        headers=admin_headers,
        json={
            "invoice_id": "inv-9999",
            "amount": 750,
            "action": "APPROVE",
            "ground_truth": "APPROVE",
            "agent_id": "agent-01",
            "reason": "smoke test",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["invoice_id"] == "inv-9999"
    assert body["action"] == "APPROVE"
    assert body["decision_id"].startswith("dec-")


def test_create_decision_requires_reason(client, admin_headers):
    resp = client.post(
        "/api/v1/decisions",
        headers=admin_headers,
        json={
            "invoice_id": "inv-9999",
            "amount": 750,
            "action": "APPROVE",
            "ground_truth": "APPROVE",
            "agent_id": "agent-01",
        },
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] == "validation_error"


def test_list_decisions(client, admin_headers):
    resp = client.get("/api/v1/decisions", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    agent_ids = {d["agent_id"] for d in body["items"]}
    assert agent_ids <= {"agent-01", "agent-02", "agent-03"}


def test_get_decision(client, admin_headers):
    resp = client.get("/api/v1/decisions/dec-agent03-0193", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    # the critical error behind agent-03's clawback: APPROVE where ground truth is REJECT
    assert body["action"] == "APPROVE"
    assert body["ground_truth"] == "REJECT"


def test_get_decision_not_found(client, admin_headers):
    resp = client.get("/api/v1/decisions/does-not-exist", headers=admin_headers)
    assert resp.status_code == 404
    assert resp.json()["code"] == "decision_not_found"
