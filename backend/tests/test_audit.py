from __future__ import annotations

import hashlib
import json


def test_list_audit_samples(client, admin_headers):
    resp = client.get("/api/v1/audit-samples", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 4
    pending = [s for s in body["items"] if s["reviewed_at"] is None]
    assert len(pending) == 2


def test_review_audit_sample_as_reviewer(client, reviewer_headers):
    resp = client.post(
        "/api/v1/audit-samples/sample-002/review",
        headers=reviewer_headers,
        json={"verdict": "AGREED", "reviewer_action": "APPROVE", "reason": "checked, correct"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["verdict"] == "AGREED"
    assert body["reviewed_at"] is not None


def test_review_audit_sample_as_admin(client, admin_headers):
    resp = client.post(
        "/api/v1/audit-samples/sample-004/review",
        headers=admin_headers,
        json={"verdict": "DISAGREED", "reviewer_action": "REJECT", "reason": "should have been rejected"},
    )
    assert resp.status_code == 200


def test_auditor_cannot_review(client, auditor_headers):
    # "auditor is read-only" (docs/lanes/vp.md)
    resp = client.post(
        "/api/v1/audit-samples/sample-002/review",
        headers=auditor_headers,
        json={"verdict": "AGREED", "reviewer_action": "APPROVE", "reason": "trying anyway"},
    )
    assert resp.status_code == 403


def test_cannot_review_an_already_reviewed_sample(client, admin_headers):
    resp = client.post(
        "/api/v1/audit-samples/sample-001/review",
        headers=admin_headers,
        json={"verdict": "AGREED", "reviewer_action": "APPROVE", "reason": "trying anyway"},
    )
    assert resp.status_code == 409


def test_review_audit_sample_not_found(client, reviewer_headers):
    resp = client.post(
        "/api/v1/audit-samples/does-not-exist/review",
        headers=reviewer_headers,
        json={"verdict": "AGREED", "reviewer_action": "APPROVE", "reason": "n/a"},
    )
    assert resp.status_code == 404


def test_audit_log_is_hash_chained(client, admin_headers):
    resp = client.get("/api/v1/audit-log", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 5
    # newest first on the wire; verify the chain in chronological order
    entries = list(reversed(body["items"]))
    prev_hash = "0" * 64
    for entry in entries:
        assert entry["prev_hash"] == prev_hash
        canonical = json.dumps(entry["payload"], sort_keys=True, separators=(",", ":"), default=str)
        expected = hashlib.sha256((prev_hash + canonical).encode("utf-8")).hexdigest()
        assert entry["hash"] == expected
        prev_hash = entry["hash"]


def test_audit_log_read_only_for_auditor(client, auditor_headers):
    # auditor is read-only, but read-only still means it can read
    resp = client.get("/api/v1/audit-log", headers=auditor_headers)
    assert resp.status_code == 200
