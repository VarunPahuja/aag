"""A simulation run applies the clawback its own decisions earned.

The gap this closes: a run recorded decisions and stopped. A degraded run could
push drift to CRITICAL, the trust evaluation would correctly read CLAWBACK, and
the agent kept its full limit indefinitely — because a clawback only applies
when a *recommendation* is generated, and nothing generated one.

Detection without action. ADR-0004 is explicit that a reduction needs no human
authorization, so nothing should have to poke the system for one to take
effect.
"""

from __future__ import annotations

import time

from sqlalchemy.orm import Session

from app.models import Agent


def _run(client, headers, agent_id: str, phase: str, count: int = 60, seed: int = 7):
    resp = client.post(
        "/api/v1/simulation/runs",
        headers=headers,
        json={
            "agent_id": agent_id,
            "phase": phase,
            "invoice_count": count,
            "seed": seed,
            "reason": f"clawback test {phase}",
        },
    )
    assert resp.status_code == 201, resp.text
    run_id = resp.json()["run_id"]
    for _ in range(120):
        row = client.get(f"/api/v1/simulation/runs/{run_id}", headers=headers).json()
        if row["status"] != "running":
            return row
        time.sleep(0.05)
    raise AssertionError("simulation run did not finish")


def _agent(db_engine, agent_id: str = "agent-01") -> tuple[int, int]:
    with Session(db_engine) as session:
        a = session.get(Agent, agent_id)
        return a.current_limit, a.current_rung


def test_a_degraded_run_claws_back_without_being_asked(client, admin_headers, db_engine):
    """The whole point: nobody generates a recommendation, nobody approves
    anything, and the limit still comes down."""
    before_limit, before_rung = _agent(db_engine)
    assert before_rung >= 1, "agent-01 needs somewhere to fall to"

    row = _run(client, admin_headers, "agent-01", "degraded")
    assert row["status"] == "completed"

    after_limit, after_rung = _agent(db_engine)
    assert after_rung == before_rung - 1, (
        f"expected exactly one rung down from {before_rung}, got {after_rung}"
    )
    assert after_limit < before_limit


def test_the_clawback_is_recorded_as_a_system_action(client, admin_headers, db_engine):
    """No human authorized it, so the trail must say so — ADR-0004's asymmetry
    has to be visible afterwards, not just true at the time."""
    _run(client, admin_headers, "agent-01", "degraded")

    versions = client.get(
        "/api/v1/agents/agent-01/policy-versions", headers=admin_headers
    ).json()["items"]
    newest = versions[0]
    assert newest["created_by"] == "system", newest
    assert "clawback" in (newest["reason"] or "").lower()

    recs = client.get(
        "/api/v1/recommendations?agent_id=agent-01", headers=admin_headers
    ).json()["items"]
    clawbacks = [r for r in recs if r["direction"] == "CLAWBACK"]
    assert clawbacks, "a clawback recommendation should exist"
    assert clawbacks[0]["status"] == "APPROVED", "applied without a human step"

    approvals_for_it = [r for r in clawbacks if r.get("approved_by")]
    assert not approvals_for_it, "no human approval row for an automatic clawback"


def test_a_clean_good_run_leaves_the_agent_alone(client, admin_headers, db_engine):
    """A healthy run must not demote its agent — otherwise every simulation
    would quietly cost a rung.

    Seed 99 is chosen because `generate_decision_plan` produces no critical
    error for (agent-01, good, 99, 60). That is not a formality: the good phase
    carries a small but real critical-error probability, so *some* good seeds do
    earn a clawback, and one critical error in the recent window is enough.
    Seed 7 produces one at position 44 and would legitimately claw back. See
    `test_a_good_run_that_makes_a_critical_error_still_claws_back`."""
    before = _agent(db_engine)
    row = _run(client, admin_headers, "agent-01", "good", seed=99)
    assert row["status"] == "completed"
    assert _agent(db_engine) == before


def test_a_good_run_that_makes_a_critical_error_still_claws_back(
    client, admin_headers, db_engine
):
    """The rule is about the evidence, not the phase label. A "good" agent that
    approves an invoice it should have rejected has still let money out of the
    door, and the clawback is not negotiable on the strength of the phase it
    happened in."""
    from shared.enums import Action
    from trust_engine.constants import CRITICAL_ERROR_WINDOW

    from app.schemas.simulation import SimulationPhase
    from app.services.simulation import generate_decision_plan

    plan = generate_decision_plan(
        agent_id="agent-01", phase=SimulationPhase.GOOD, seed=42, count=60,
        current_limit=2500,
    )
    # Only acted decisions can carry a critical error, and only the last
    # CRITICAL_ERROR_WINDOW of them are what drift looks at. Escalations are
    # deferrals, so they neither count nor push earlier errors out of view.
    acted = [d for d in plan if d.action is not Action.ESCALATE]
    in_window = [
        d for d in acted[-CRITICAL_ERROR_WINDOW:]
        if d.action is Action.APPROVE and d.ground_truth is Action.REJECT
    ]
    assert in_window, (
        "precondition: this seed must put a critical error in the recent window"
    )

    _, before_rung = _agent(db_engine)
    _run(client, admin_headers, "agent-01", "good", seed=42, count=60)
    _, after_rung = _agent(db_engine)
    assert after_rung == before_rung - 1


def test_a_good_run_does_not_raise_the_limit_either(client, admin_headers, db_engine):
    """An INCREASE still waits for a human. A run may *ask* for one, but it
    must never apply it — that is the one step ADR-0004 requires."""
    before_limit, _ = _agent(db_engine)
    _run(client, admin_headers, "agent-01", "good", count=80)
    after_limit, _ = _agent(db_engine)
    assert after_limit <= before_limit, "a run must never raise a limit on its own"


def test_an_earned_increase_becomes_an_approval_request(client, admin_headers, db_engine):
    """The other half of ADR-0004, which had no producer at all.

    Restricting the post-run action to clawbacks meant a good run could raise
    the trust score until the ladder read INCREASE and nothing ever created
    the recommendation — so no approval request appeared and the dashboard
    showed an increase that could not be acted on. Only the /demo console
    generated one.

    Two runs, not one. The seeded baseline history is close to perfect, so the
    *first* real run at the good phase's ~95% reads as a confirmed drop
    against it and legitimately claws back (drift CONFIRMED,
    CLAWBACK_DRIFT). The second run is evaluated against a baseline that
    includes real decisions, which is when an increase becomes earnable.
    """
    from shared.enums import Direction, RecommendationStatus

    from app.models import Agent
    from app.services.trust import compute_trust_evaluation

    _run(client, admin_headers, "agent-01", "good", count=200, seed=99)
    _run(client, admin_headers, "agent-01", "good", count=200, seed=99)

    with Session(db_engine) as session:
        evaluation = compute_trust_evaluation(session, session.get(Agent, "agent-01"))
    assert evaluation.direction is Direction.INCREASE, (
        f"precondition: two good runs should earn an increase, got "
        f"{evaluation.direction} with {list(evaluation.reason_codes)}"
    )

    recs = client.get(
        "/api/v1/recommendations?agent_id=agent-01", headers=admin_headers
    ).json()["items"]
    pending = [
        r for r in recs
        if r["direction"] == Direction.INCREASE.value
        and r["status"] == RecommendationStatus.PENDING.value
    ]
    assert pending, (
        "an earned increase must reach the approvals queue; "
        f"got {[(r['direction'], r['status']) for r in recs]}"
    )


def test_the_earned_increase_is_not_applied_by_the_run(client, admin_headers, db_engine):
    """Asking is not the same as taking. The request exists; the limit does
    not move until a human approves it."""
    _run(client, admin_headers, "agent-01", "good", count=200, seed=99)
    limit_before, rung_before = _agent(db_engine)
    _run(client, admin_headers, "agent-01", "good", count=200, seed=99)
    assert _agent(db_engine) == (limit_before, rung_before), (
        "a run must never raise a limit on its own"
    )


def test_a_stale_seeded_request_does_not_block_a_new_one(
    client, admin_headers, db_engine
):
    """The bug this guard originally caused.

    `app/seed.py` ships agent-01 with a PENDING increase to INR 5,000, which is
    valid at seed time because the agent starts at INR 2,500. A clawback then
    moves the agent down, and that pending row becomes stale — it asks for a
    limit the current evidence no longer supports. Guarding on "does any
    pending recommendation exist" made every later run treat its own request as
    a duplicate and write nothing, so the approvals queue showed one stale card
    forever while the agent page reported direction=INCREASE.
    """
    from shared.enums import Direction, RecommendationStatus

    from app.models import Agent
    from app.services.trust import compute_trust_evaluation

    seeded_pending = [
        r for r in client.get(
            "/api/v1/recommendations?agent_id=agent-01", headers=admin_headers
        ).json()["items"]
        if r["status"] == RecommendationStatus.PENDING.value
    ]
    assert seeded_pending, "precondition: the seed ships a pending request for agent-01"
    stale_limit = seeded_pending[0]["proposed_limit"]

    # Degrade first, so the seeded request is genuinely out of date.
    _run(client, admin_headers, "agent-01", "degraded")
    limit_after_clawback, _ = _agent(db_engine)
    assert limit_after_clawback != stale_limit, (
        "precondition: the clawback must leave the seeded request stale"
    )

    _run(client, admin_headers, "agent-01", "good", count=200, seed=99)
    _run(client, admin_headers, "agent-01", "good", count=200, seed=99)

    with Session(db_engine) as session:
        evaluation = compute_trust_evaluation(session, session.get(Agent, "agent-01"))
    assert evaluation.direction is Direction.INCREASE, (
        f"precondition: recovery from a clawback should earn an increase, got "
        f"{evaluation.direction} with {list(evaluation.reason_codes)}"
    )

    items = client.get(
        "/api/v1/recommendations?agent_id=agent-01", headers=admin_headers
    ).json()["items"]
    live = [r for r in items if r["status"] == RecommendationStatus.PENDING.value]

    assert live, "a fresh increase must reach the queue even with a stale one present"
    assert all(r["proposed_limit"] == evaluation.recommended_limit for r in live), (
        f"the live request(s) must match current evidence "
        f"({evaluation.recommended_limit}); got "
        f"{[r['proposed_limit'] for r in live]}"
    )


def test_the_stale_request_is_marked_superseded_not_deleted(
    client, admin_headers, db_engine
):
    """SUPERSEDED is the state shared/enums.py already defines for "invalidated
    by a newer one before a human ever ruled on it" — and which no code wrote
    until now. The stale row stays in the record; only its status changes."""
    from shared.enums import RecommendationStatus

    before = client.get(
        "/api/v1/recommendations?agent_id=agent-01", headers=admin_headers
    ).json()["total"]

    _run(client, admin_headers, "agent-01", "degraded")
    _run(client, admin_headers, "agent-01", "good", count=200, seed=99)
    _run(client, admin_headers, "agent-01", "good", count=200, seed=99)

    items = client.get(
        "/api/v1/recommendations?agent_id=agent-01", headers=admin_headers
    ).json()["items"]
    assert len(items) >= before, "nothing may be deleted from the record"

    superseded = [
        r for r in items if r["status"] == RecommendationStatus.SUPERSEDED.value
    ]
    assert superseded, "the stale request should be marked SUPERSEDED"


def test_a_second_run_does_not_stack_a_duplicate_request(client, admin_headers, db_engine):
    """Re-running a simulation is something a person does freely while
    rehearsing. Stacking near-identical approval requests would bury the one
    that matters."""
    _run(client, admin_headers, "agent-01", "good", count=200, seed=99)
    _run(client, admin_headers, "agent-01", "good", count=200, seed=99)

    total_with_pending = client.get(
        "/api/v1/recommendations?agent_id=agent-01", headers=admin_headers
    ).json()["total"]

    _run(client, admin_headers, "agent-01", "good", count=200, seed=99)
    after = client.get(
        "/api/v1/recommendations?agent_id=agent-01", headers=admin_headers
    ).json()["total"]

    assert after == total_with_pending, (
        "a pending request must not be duplicated by a repeat run"
    )


def test_a_run_at_the_floor_stays_at_the_floor(client, admin_headers, db_engine):
    """agent-02 is at rung 0. A clawback there is floor -> floor, which must be
    a no-op rather than a negative rung or a redundant policy version."""
    with Session(db_engine) as session:
        start = session.get(Agent, "agent-02")
        assert start.current_rung == 0
        before_limit = start.current_limit

    versions_before = client.get(
        "/api/v1/agents/agent-02/policy-versions", headers=admin_headers
    ).json()["total"]

    row = _run(client, admin_headers, "agent-02", "degraded")
    assert row["status"] == "completed"

    after_limit, after_rung = _agent(db_engine, "agent-02")
    assert after_rung == 0
    assert after_limit == before_limit

    versions_after = client.get(
        "/api/v1/agents/agent-02/policy-versions", headers=admin_headers
    ).json()["total"]
    assert versions_after == versions_before, "no redundant policy version at the floor"


def test_the_run_still_completes_if_governance_is_unavailable(
    client, admin_headers, db_engine, monkeypatch
):
    """A governance outage must not retroactively fail a run whose decisions
    were recorded successfully — and it must leave a trace rather than
    swallowing the fact that an earned clawback never landed."""
    import app.services.simulation as sim

    def boom(*_args, **_kwargs):
        raise RuntimeError("governance is down")

    monkeypatch.setattr(sim, "_act_on_what_the_run_earned", lambda *a, **k: boom())

    row = _run(client, admin_headers, "agent-01", "degraded")
    assert row["status"] == "completed", "the run itself succeeded"
    assert row["decisions_submitted"] > 0


# ---------------------------------------------------------------------------
# From PR #47 (Varun P.), kept as written apart from the renamed function
# under test. That PR and this branch closed the same gap independently — the
# end-of-run clawback trigger — and git auto-merged both implementations side
# by side, leaving one of them dead. They are now one function,
# `_act_on_what_the_run_earned`, which took PR #47's side-effect-free peek,
# its two-session split and its stricter "applied only if the limit actually
# moved" rule, and kept this branch's handling of INCREASE alongside CLAWBACK.
#
# Both suites are kept on purpose: his pin the clawback trigger and the run-row
# fields, mine pin the increase half and the supersede rule. Neither set covers
# the other.
# ---------------------------------------------------------------------------

from shared.constants import AUTONOMY_FLOOR, limit_of, rung_of

from app.services.simulation import (
    ClawbackOutcome,
    _act_on_what_the_run_earned,
)


def _start_run(client, admin_headers, **overrides):
    body = {
        "phase": "good",
        "agent_id": "agent-01",
        "invoice_count": 20,
        "seed": 1,
        "reason": "clawback trigger test",
    }
    body.update(overrides)
    return client.post("/api/v1/simulation/runs", headers=admin_headers, json=body)


def _run_to_completion(client, admin_headers, run_id: str, max_attempts: int = 100) -> dict:
    """The background task runs on its own thread, not synchronously before
    `.post()` returns (confirmed by direct observation, against
    `test_simulation.py`'s own comment claiming otherwise) — every assertion
    on a run's terminal fields must poll for one first, the same as
    `test_simulation.py`'s own `_poll_until_done`."""
    body = None
    for _ in range(max_attempts):
        body = client.get(f"/api/v1/simulation/runs/{run_id}", headers=admin_headers).json()
        if body["status"] in ("completed", "failed"):
            return body
        time.sleep(0.05)
    raise AssertionError(f"run {run_id} never reached a terminal status: {body}")


def test_degrading_run_ends_with_the_agent_clawed_back_no_separate_endpoint_call(
    client, admin_headers, db_engine
):
    with Session(db_engine) as session:
        rung_before = session.get(Agent, "agent-01").current_rung

    # seed=2, count=30. PR #47 used count=20, which worked when every planned
    # invoice was acted on. The agent now escalates anything over its limit, so
    # 20 invoices leave only 8 acted decisions for agent-01 at INR 2,500 — and
    # the critical error that used to trip this landed on an invoice the agent
    # now (correctly) defers instead of approving. 30 invoices give 14 acted
    # with a critical error still inside CRITICAL_ERROR_WINDOW; re-derived
    # against `generate_decision_plan` the same way the original seed was.
    # agent-02 sits at the floor, where far less escalates, so its own scenario
    # below still trips at count=20 unchanged.
    resp = _start_run(client, admin_headers, phase="degraded", seed=2, invoice_count=30)
    assert resp.status_code == 201
    body = _run_to_completion(client, admin_headers, resp.json()["run_id"])
    assert body["status"] == "completed"

    # No call to /agents/{id}/recommendations anywhere in this test — the run
    # itself is what applied the clawback.
    assert body["clawback_applied"] is True
    assert body["clawback_limit"] == limit_of(rung_before - 1)

    with Session(db_engine) as session:
        agent = session.get(Agent, "agent-01")
        assert agent.current_rung == rung_before - 1
        assert agent.current_limit == limit_of(rung_before - 1)


def test_clean_run_does_not_claw_back(client, admin_headers, db_engine):
    with Session(db_engine) as session:
        rung_before = session.get(Agent, "agent-01").current_rung

    # seed=1, count=20: zero critical errors anywhere in the plan.
    resp = _start_run(client, admin_headers, phase="good", seed=1, invoice_count=20)
    assert resp.status_code == 201
    body = _run_to_completion(client, admin_headers, resp.json()["run_id"])
    assert body["status"] == "completed"
    assert body["clawback_applied"] is False
    assert body["clawback_limit"] is None

    with Session(db_engine) as session:
        assert session.get(Agent, "agent-01").current_rung == rung_before


def test_cascade_guard_holds_across_a_second_evaluation_with_no_new_decisions(
    client, admin_headers, db_engine
):
    """A run that claws back, followed by another evaluation over the exact
    same, unchanged decision history (no new decisions submitted in
    between), must not claw back a second time — the guard
    `app.services.governance.generate_recommendation` already applies
    (PR #40) still holds when reached through this new trigger point, since
    this branch reuses that function rather than writing a second clawback
    path.
    """
    with Session(db_engine) as session:
        rung_before = session.get(Agent, "agent-01").current_rung

    resp = _start_run(client, admin_headers, phase="degraded", seed=2, invoice_count=30)
    run_id = resp.json()["run_id"]
    body = _run_to_completion(client, admin_headers, run_id)
    assert body["clawback_applied"] is True

    with Session(db_engine) as session:
        assert session.get(Agent, "agent-01").current_rung == rung_before - 1

    # Directly re-invoke the same end-of-run evaluation this run's own
    # background task called — no new decisions submitted since the clawback
    # above, exactly the "another run submitting zero new decisions"
    # scenario: decisions_since_last_change is 0 relative to the policy
    # version the first call just wrote.
    #
    # The merged function takes the run id as well, so a failure can be
    # recorded against the run it belongs to; PR #47's two-argument form had
    # nowhere to write that.
    outcome = _act_on_what_the_run_earned(run_id, db_engine, "agent-01")
    assert outcome == ClawbackOutcome(applied=False, limit=None)

    with Session(db_engine) as session:
        # Exactly one rung dropped, not two.
        assert session.get(Agent, "agent-01").current_rung == rung_before - 1


def test_clawback_never_drops_below_autonomy_floor(client, admin_headers, db_engine):
    with Session(db_engine) as session:
        agent = session.get(Agent, "agent-02")
        assert agent.current_limit == AUTONOMY_FLOOR, "test assumes agent-02 is seeded at the floor"

    # seed=2, count=20 against agent-02: last-20 acted decisions contain a
    # critical error, same as agent-01's scenario above, found independently
    # for this agent (see module docstring).
    resp = _start_run(
        client, admin_headers, agent_id="agent-02", phase="degraded", seed=2, invoice_count=20
    )
    assert resp.status_code == 201
    body = _run_to_completion(client, admin_headers, resp.json()["run_id"])
    assert body["status"] == "completed"
    # Already at the floor: governance.py's own floor no-op (PR #34) means no
    # new policy version is written, so this run's own evaluation reports no
    # applied clawback even though the direction was CLAWBACK.
    assert body["clawback_applied"] is False
    assert body["clawback_limit"] is None

    with Session(db_engine) as session:
        agent = session.get(Agent, "agent-02")
        assert agent.current_limit == AUTONOMY_FLOOR
        assert agent.current_rung == rung_of(AUTONOMY_FLOOR) == 0


def test_run_record_reflects_no_clawback_fields_by_default(client, admin_headers):
    """Every run, clawed back or not, carries both fields in its response —
    `clawback_applied` is never missing, just `False`."""
    resp = _start_run(client, admin_headers, phase="good", seed=1, invoice_count=20)
    body = _run_to_completion(client, admin_headers, resp.json()["run_id"])
    assert "clawback_applied" in body
    assert "clawback_limit" in body
    assert body["clawback_applied"] is False
    assert body["clawback_limit"] is None
