"""The rules that apply to every endpoint, tested once rather than
re-asserted per resource: the pagination envelope, the error body shape,
and the stub-identity header."""

from __future__ import annotations

import pytest


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/agents",
        "/api/v1/decisions",
        "/api/v1/recommendations",
        "/api/v1/audit-samples",
    ],
)
def test_every_list_endpoint_uses_the_one_pagination_envelope(client, admin_headers, path):
    resp = client.get(path, headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {"items", "total", "page", "page_size"}
    assert isinstance(body["items"], list)


def test_audit_log_extends_the_envelope_with_chain_verification(client, admin_headers):
    # The one deliberate exception to "one pagination envelope everywhere"
    # (docs/lanes/vp.md): audit-log has to report whether the hash chain
    # verifies, which is not a list-endpoint concern any other resource has.
    resp = client.get("/api/v1/audit-log", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {"items", "total", "page", "page_size", "chain_valid", "chain_verified_scope"}
    assert isinstance(body["items"], list)


def test_default_role_without_a_header_is_admin(client):
    # Dev convenience: /docs and a bare curl work without extra setup.
    resp = client.get("/api/v1/agents")
    assert resp.status_code == 200


def test_unrecognized_role_header_is_rejected_loudly(client):
    resp = client.get("/api/v1/agents", headers={"X-User-Role": "superuser"})
    assert resp.status_code == 401
    body = resp.json()
    assert set(body.keys()) == {"code", "message", "detail"}
    assert body["code"] == "invalid_role_header"


def test_404_uses_the_one_error_body(client, admin_headers):
    resp = client.get("/api/v1/agents/does-not-exist", headers=admin_headers)
    assert set(resp.json().keys()) == {"code", "message", "detail"}


def test_403_uses_the_one_error_body(client, reviewer_headers):
    resp = client.post(
        "/api/v1/recommendations/rec-agent01-001/approve",
        headers=reviewer_headers,
        json={"reason": "trying anyway"},
    )
    assert set(resp.json().keys()) == {"code", "message", "detail"}


def test_422_uses_the_one_error_body(client, admin_headers):
    resp = client.post(
        "/api/v1/recommendations/rec-agent01-001/approve", headers=admin_headers, json={}
    )
    assert set(resp.json().keys()) == {"code", "message", "detail"}
    assert resp.json()["code"] == "validation_error"
