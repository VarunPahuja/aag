"""The `contested_increase` scenario is the only place dissent can be observed.

`_aggregate` lets an OBJECT bite on `Direction.INCREASE` and nowhere else. Of the
original five scenarios exactly one was an INCREASE, and the recorded panel concurred
unanimously on it — so in cached mode the conservatism ratchet never fired anywhere.
Stub mode hard-codes an objection, which is why nobody noticed.

This scenario restores an increase a reasonable agent can refuse: a wide interval on an
adequate sample. These tests pin the properties that make it refusable. They are not a
claim about what the model *will* say — that is what the recordings are for. They are a
guard so a trust-engine tuning pass (`trust/trust_engine/constants.py` is explicitly
expected to change in week 3) cannot quietly turn this back into a unanimous scenario
and leave the demo showing a mechanism that no longer runs.

Every number here is read off the `TrustEvaluation`. Nothing in this lane derives one.
"""

from __future__ import annotations

from shared.contracts import Direction
from trust_engine.constants import (
    MIN_SAMPLE_FOR_INCREASE,
    MIN_TRUST_SCORE_FOR_INCREASE,
)

from governance.scenarios import SCENARIOS, SCENARIOS_BY_NAME

SCENARIO = "contested_increase"


def _evaluation():
    return SCENARIOS_BY_NAME[SCENARIO].build()


def test_the_engine_actually_proposes_an_increase():
    """Without this, dissent cannot bite no matter what the agents say."""
    evaluation = _evaluation()

    assert evaluation.direction is Direction.INCREASE
    assert evaluation.eligible_for_increase is True
    assert evaluation.recommended_limit > evaluation.current_limit


def test_it_clears_every_gate_the_engine_checks():
    """It has to be a *legitimate* proposal, not one that squeaked through."""
    evaluation = _evaluation()

    assert evaluation.acted_decisions >= MIN_SAMPLE_FOR_INCREASE
    assert evaluation.trust_score >= MIN_TRUST_SCORE_FOR_INCREASE
    assert evaluation.critical_errors == 0
    assert evaluation.critical_errors_in_recent_window == 0


def test_the_interval_is_wide_enough_to_argue_about():
    """The lower bound is the objection. If it climbs, the scenario stops contesting.

    0.80 is not a threshold the system enforces anywhere — it is a tripwire for this
    test. An interval whose lower bound sits comfortably above it is a record the
    Performance agent has no honest reason to refuse, and the scenario has stopped
    doing its job.
    """
    accuracy = _evaluation().accuracy

    assert accuracy.wilson_lower < 0.80


def test_drift_is_silent_so_the_objection_is_only_about_precision():
    """Errors are spread evenly on purpose.

    If drift fired, the engine would block the increase on its own and the panel would
    never be asked. It would also confound the demo: the audience could not tell whether
    the objection was about imprecision or about degradation.
    """
    drift = _evaluation().drift

    assert drift.detected is False
    assert drift.underpowered is False


def test_it_is_the_only_scenario_where_dissent_can_bite():
    """If a second INCREASE scenario appears, this test is the place to reconsider.

    Not a rule that there must only ever be one — a reminder that the count is load
    bearing, because a scenario list with no INCREASE in it silently disables the
    ratchet.
    """
    increases = [s.name for s in SCENARIOS if s.build().direction is Direction.INCREASE]

    assert SCENARIO in increases
    assert increases == ["healthy_increase", SCENARIO]
