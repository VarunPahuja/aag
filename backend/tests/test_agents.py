from __future__ import annotations

from shared.constants import AUTONOMY_LADDER


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
    resp = client.get("/api/v1/agents/agent-01/trust", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["agent_id"] == "agent-01"
    assert body["direction"] == "INCREASE"
    assert body["eligible_for_increase"] is True
    assert "id" in body  # backend-minted, not on the shared dataclass


def test_list_trust_history(client, admin_headers):
    resp = client.get("/api/v1/agents/agent-03/trust/history", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3
    directions = [item["direction"] for item in body["items"]]
    assert "CLAWBACK" in directions
