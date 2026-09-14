"""A recommendation may not move an agent more than one rung, however old it is.

ADR-0004 caps a change at one rung per evaluation, and `trust_engine.ladder`
applies that cap when the recommendation is written. Nothing re-checked it at
*approval* time — and a PENDING row can outlive the evidence that produced it.

The concrete case this closes: `app/seed.py` ships agent-01 with a PENDING
increase to INR 5,000, correct at seed time because the agent starts at INR
2,500. A clawback then drops it to INR 1,000, and approving that still-pending
card would have jumped rung 1 straight to rung 3 in one click — two rungs the
evidence never supported, applied by a single human action that looks entirely
ordinary on screen.

`_pending_request_already_covers` marks such rows SUPERSEDED as soon as any run
re-evaluates the agent, which removes the card first. That is a race, not a
guarantee: nothing forces a run to happen in between. These tests pin the
guarantee.
"""

from __future__ import annotations

from shared.constants import limit_of, rung_of
from shared.enums import RecommendationStatus
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Agent, Recommendation


def _seeded_pending(client, admin_headers) -> dict:
    items = client.get(
        "/api/v1/recommendations?agent_id=agent-01", headers=admin_headers
    ).json()["items"]
    pending = [r for r in items if r["status"] == RecommendationStatus.PENDING.value]
    assert pending, "precondition: the seed ships a pending request for agent-01"
    return pending[0]


def _force_agent_to_rung(db_engine, agent_id: str, rung: int) -> None:
    """Move an agent directly, the sanctioned way, so a pending row becomes
    stale without depending on a simulation run to get there."""
    from datetime import UTC, datetime

    from app.models.policy_versions import apply_policy_version

    with Session(db_engine) as session:
        agent = session.get(Agent, agent_id)
        apply_policy_version(
            session,
            agent,
            id=f"pv-test-{rung}",
            limit=limit_of(rung),
            rung=rung,
            effective_from=datetime.now(UTC),
            created_by="system",
            reason="test setup: make the seeded pending recommendation stale",
        )
        session.commit()


class TestTheGuard:
    def test_a_stale_recommendation_cannot_be_approved(
        self, client, admin_headers, db_engine
    ):
        """The whole point. Two rungs apart is refused, not applied."""
        pending = _seeded_pending(client, admin_headers)
        proposed_rung = rung_of(pending["proposed_limit"])
        _force_agent_to_rung(db_engine, "agent-01", proposed_rung - 2)

        resp = client.post(
            f"/api/v1/recommendations/{pending['recommendation_id']}/approve",
            headers=admin_headers,
            json={"reason": "approving a card that is two rungs out of date"},
        )
        assert resp.status_code == 409, resp.text
        assert resp.json()["code"] == "recommendation_stale"

    def test_the_refusal_leaves_the_agent_untouched(
        self, client, admin_headers, db_engine
    ):
        """A refused approval must change nothing — no limit move, no policy
        version, and the recommendation still PENDING so a human can see why."""
        pending = _seeded_pending(client, admin_headers)
        proposed_rung = rung_of(pending["proposed_limit"])
        _force_agent_to_rung(db_engine, "agent-01", proposed_rung - 2)

        with Session(db_engine) as session:
            before = session.get(Agent, "agent-01")
            limit_before, rung_before = before.current_limit, before.current_rung
        versions_before = client.get(
            "/api/v1/agents/agent-01/policy-versions", headers=admin_headers
        ).json()["total"]

        client.post(
            f"/api/v1/recommendations/{pending['recommendation_id']}/approve",
            headers=admin_headers,
            json={"reason": "should be refused"},
        )

        with Session(db_engine) as session:
            after = session.get(Agent, "agent-01")
            assert (after.current_limit, after.current_rung) == (limit_before, rung_before)
            row = session.get(Recommendation, pending["recommendation_id"])
            assert row.status is RecommendationStatus.PENDING, (
                "a refused approval must not resolve the recommendation"
            )

        versions_after = client.get(
            "/api/v1/agents/agent-01/policy-versions", headers=admin_headers
        ).json()["total"]
        assert versions_after == versions_before, "no policy version may be written"

    def test_the_error_says_how_far_out_of_date_it_is(self, client, admin_headers, db_engine):
        """A 409 that does not say why is a dead end for whoever is looking at
        the screen."""
        pending = _seeded_pending(client, admin_headers)
        proposed_rung = rung_of(pending["proposed_limit"])
        _force_agent_to_rung(db_engine, "agent-01", proposed_rung - 3)

        resp = client.post(
            f"/api/v1/recommendations/{pending['recommendation_id']}/approve",
            headers=admin_headers,
            json={"reason": "three rungs out"},
        )
        detail = resp.json()["detail"]
        assert detail["rung_delta"] == 3
        assert detail["proposed_rung"] == proposed_rung
        assert detail["current_rung"] == proposed_rung - 3


class TestWhatMustStillWork:
    """The guard is narrow on purpose. Everything one rung or less still goes
    through, or it would break the ladder it is meant to protect."""

    def test_a_one_rung_increase_is_still_approved(self, client, admin_headers, db_engine):
        pending = _seeded_pending(client, admin_headers)
        proposed_rung = rung_of(pending["proposed_limit"])
        _force_agent_to_rung(db_engine, "agent-01", proposed_rung - 1)

        resp = client.post(
            f"/api/v1/recommendations/{pending['recommendation_id']}/approve",
            headers=admin_headers,
            json={"reason": "exactly one rung, the normal case"},
        )
        assert resp.status_code == 200, resp.text

        with Session(db_engine) as session:
            assert session.get(Agent, "agent-01").current_rung == proposed_rung

    def test_a_no_op_hold_approval_is_still_allowed(self, client, admin_headers, db_engine):
        """A HOLD proposes the agent's current limit — zero rungs apart. It
        writes no policy version but is still a real human decision worth
        recording, and the guard must not block it."""
        pending = _seeded_pending(client, admin_headers)
        proposed_rung = rung_of(pending["proposed_limit"])
        _force_agent_to_rung(db_engine, "agent-01", proposed_rung)

        resp = client.post(
            f"/api/v1/recommendations/{pending['recommendation_id']}/approve",
            headers=admin_headers,
            json={"reason": "same rung, a no-op approval"},
        )
        assert resp.status_code == 200, resp.text

    def test_rejecting_a_stale_recommendation_is_always_allowed(
        self, client, admin_headers, db_engine
    ):
        """Rejecting is how a human clears a stale card. Blocking that would
        leave it stuck in the queue for ever."""
        pending = _seeded_pending(client, admin_headers)
        proposed_rung = rung_of(pending["proposed_limit"])
        _force_agent_to_rung(db_engine, "agent-01", proposed_rung - 2)

        resp = client.post(
            f"/api/v1/recommendations/{pending['recommendation_id']}/reject",
            headers=admin_headers,
            json={"reason": "out of date, clearing it"},
        )
        assert resp.status_code == 200, resp.text

        with Session(db_engine) as session:
            row = session.get(Recommendation, pending["recommendation_id"])
            assert row.status is RecommendationStatus.REJECTED


def test_no_seeded_recommendation_is_born_stale(client, admin_headers, db_engine):
    """A guard that the seed itself trips would be unusable. Every pending row
    the seed ships must be at most one rung from its agent."""
    with Session(db_engine) as session:
        rows = (
            session.execute(
                select(Recommendation).where(
                    Recommendation.status == RecommendationStatus.PENDING
                )
            )
            .scalars()
            .all()
        )
        for row in rows:
            agent = session.get(Agent, row.agent_id)
            delta = abs(rung_of(row.proposed_limit) - agent.current_rung)
            assert delta <= 1, (
                f"seeded recommendation {row.id} is {delta} rungs from "
                f"{row.agent_id}'s current rung — it could never be approved"
            )
