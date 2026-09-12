"""The three phases have to be distinguishable, or the feature is decorative.

`degraded` previously produced about 86% accuracy against `good`'s 95%, and put
a critical error on only 2.4% of decisions — so the chance of one landing
inside CRITICAL_ERROR_WINDOW was under half, and a "degraded" run usually
finished with no drift, no clawback and a trust score that had barely moved.
On a dashboard the three phases were indistinguishable.

Every rate below is measured over *acted* decisions — an ESCALATE is a
deferral, not a right or wrong answer, and CRITICAL_ERROR_WINDOW counts only
acted decisions too.

These tests pin the property the phase names promise, not the exact numbers:
degraded must be clearly worse, and must reliably produce the critical errors
drift detection exists to catch.
"""

from __future__ import annotations

import pytest
from shared.enums import Action

from app.schemas.simulation import SimulationPhase
from app.services.simulation import _PHASE_PARAMS, generate_decision_plan

COUNT = 400
SEED = 42


def _plan(phase: SimulationPhase):
    return generate_decision_plan(
        agent_id="agent-01", phase=phase, seed=SEED, count=COUNT, current_limit=2500
    )


def _acted(plan):
    """Decisions the agent actually made. An ESCALATE is a deferral to a human,
    not a right or wrong answer, and `trust_engine.stats.rates` excludes it from
    accuracy for exactly that reason — so every rate here is over acted
    decisions, matching what CRITICAL_ERROR_WINDOW counts."""
    return [d for d in plan if d.action is not Action.ESCALATE]


def _accuracy(plan) -> float:
    acted = _acted(plan)
    return sum(1 for d in acted if d.action is d.ground_truth) / len(acted)


def _critical_rate(plan) -> float:
    acted = _acted(plan)
    return sum(
        1 for d in acted if d.action is Action.APPROVE and d.ground_truth is Action.REJECT
    ) / len(acted)


def _critical_in_window(plan, window: int) -> int:
    acted = _acted(plan)
    return sum(
        1
        for d in acted[-window:]
        if d.action is Action.APPROVE and d.ground_truth is Action.REJECT
    )


@pytest.mark.parametrize("phase", list(SimulationPhase))
def test_every_phase_produces_a_full_plan(phase):
    assert len(_plan(phase)) == COUNT


def test_degraded_is_clearly_worse_than_good():
    """Not "a bit lower" — far enough apart to be obvious on a chart."""
    good = _accuracy(_plan(SimulationPhase.GOOD))
    degraded = _accuracy(_plan(SimulationPhase.DEGRADED))
    assert good - degraded > 0.20, f"good {good:.3f} vs degraded {degraded:.3f}"


def test_recovery_climbs_back_toward_good():
    good = _accuracy(_plan(SimulationPhase.GOOD))
    degraded = _accuracy(_plan(SimulationPhase.DEGRADED))
    recovery = _accuracy(_plan(SimulationPhase.RECOVERY))
    assert recovery > degraded + 0.15, "recovery must be a visible improvement"
    assert recovery <= good + 0.02, "and must not exceed the good phase"


def test_degraded_reliably_puts_a_critical_error_in_the_recent_window():
    """The clawback beat depends on this, so assert it directly rather than
    through a probability estimate.

    This used to infer the chance from a per-decision rate, which stopped
    meaning anything once the plan began escalating over-limit invoices: those
    are not acted decisions, so they dilute a rate measured over the whole plan
    while changing nothing about the window, which only ever counted acted
    ones. Measured over acted decisions the risk is unchanged — but the honest
    test is simply to look in the window, across the limits an agent can
    actually hold.
    """
    from trust_engine.constants import CRITICAL_ERROR_WINDOW

    misses = [
        (seed, limit, count)
        for seed in (7, 42, 99, 11, 2026)
        for limit in (500, 1000, 2500, 5000)
        for count in (60, 100, 200)
        if _critical_in_window(
            generate_decision_plan(
                agent_id="agent-01",
                phase=SimulationPhase.DEGRADED,
                seed=seed,
                count=count,
                current_limit=limit,
            ),
            CRITICAL_ERROR_WINDOW,
        )
        == 0
    ]
    assert not misses, (
        f"{len(misses)} degraded configurations would finish with no drift at "
        f"all, e.g. {misses[:3]}"
    )


def test_the_agent_escalates_exactly_what_it_may_not_decide():
    """The escalation rule itself: over the limit is deferred, at or under it is
    decided. This is what gives `human_agreement` any evidence to work with —
    without it the trust score's fourth component is permanently unavailable and
    the governance audit agent objects to every increase for ever."""
    for limit in (500, 1000, 2500, 5000, 10000):
        plan = generate_decision_plan(
            agent_id="agent-01",
            phase=SimulationPhase.GOOD,
            seed=SEED,
            count=200,
            current_limit=limit,
        )
        escalated = [d for d in plan if d.action is Action.ESCALATE]
        assert all(d.amount > limit for d in escalated), f"limit {limit}"
        assert all(d.amount <= limit for d in _acted(plan)), f"limit {limit}"
        assert all(
            d.recommended_action in (Action.APPROVE, Action.REJECT) for d in escalated
        ), "an escalation must carry what the agent would have done"


def test_good_and_recovery_stay_safe():
    """A clawback in a good or recovery run would break the arc's story, so
    critical errors there must stay rare."""
    for phase in (SimulationPhase.GOOD, SimulationPhase.RECOVERY):
        assert _critical_rate(_plan(phase)) < 0.03, phase


def test_plans_are_reproducible():
    a = _plan(SimulationPhase.DEGRADED)
    b = _plan(SimulationPhase.DEGRADED)
    assert [(d.invoice_id, d.action, d.ground_truth, d.amount) for d in a] == [
        (d.invoice_id, d.action, d.ground_truth, d.amount) for d in b
    ]


def test_different_agents_get_different_plans():
    """The generator is seeded with agent_id too, so one seed does not give
    every agent an identical run."""
    one = generate_decision_plan(
        agent_id="agent-01", phase=SimulationPhase.GOOD, seed=SEED, count=50, current_limit=2500
    )
    two = generate_decision_plan(
        agent_id="agent-02", phase=SimulationPhase.GOOD, seed=SEED, count=50, current_limit=2500
    )
    assert [d.amount for d in one] != [d.amount for d in two]


def test_every_phase_declares_all_three_probabilities():
    """A missing key would be a KeyError deep inside a background task, where
    nobody would see it."""
    for phase, params in _PHASE_PARAMS.items():
        assert set(params) == {
            "p_ground_truth_reject",
            "p_critical_error",
            "p_noncritical_error",
        }, phase
        for name, value in params.items():
            assert 0.0 <= value <= 1.0, f"{phase} {name} = {value}"
