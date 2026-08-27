from __future__ import annotations


def test_list_recommendations(client, admin_headers):
    resp = client.get("/api/v1/recommendations", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
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
