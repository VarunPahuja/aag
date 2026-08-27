from __future__ import annotations

from shared.constants import SCHEMA_VERSION


def test_health(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body == {"status": "ok", "schema_version": SCHEMA_VERSION}


def test_health_requires_no_auth(client):
    # No X-User-Role header at all, and it still succeeds.
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
