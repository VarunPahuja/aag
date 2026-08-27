from __future__ import annotations


def test_start_simulation_run_as_admin(client, admin_headers):
    resp = client.post(
        "/api/v1/simulation/runs",
        headers=admin_headers,
        json={"phase": "good", "agent_id": "agent-01", "invoice_count": 50, "seed": 7, "reason": "smoke test"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "pending"
    assert body["run_id"].startswith("run-")


def test_start_simulation_run_requires_reason(client, admin_headers):
    resp = client.post(
        "/api/v1/simulation/runs",
        headers=admin_headers,
        json={"phase": "good", "agent_id": "agent-01", "invoice_count": 50, "seed": 7},
    )
    assert resp.status_code == 422


def test_reviewer_cannot_start_a_run(client, reviewer_headers):
    resp = client.post(
        "/api/v1/simulation/runs",
        headers=reviewer_headers,
        json={"phase": "good", "agent_id": "agent-01", "invoice_count": 50, "seed": 7, "reason": "trying anyway"},
    )
    assert resp.status_code == 403


def test_get_simulation_run(client, admin_headers):
    resp = client.get("/api/v1/simulation/runs/run-0001", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "completed"
    assert body["accuracy"] == 0.94


def test_get_simulation_run_still_running(client, admin_headers):
    resp = client.get("/api/v1/simulation/runs/run-0002", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "running"
    assert body["accuracy"] is None


def test_get_simulation_run_not_found(client, admin_headers):
    resp = client.get("/api/v1/simulation/runs/does-not-exist", headers=admin_headers)
    assert resp.status_code == 404
