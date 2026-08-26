"""The autonomy ladder: rungs, gates, clawbacks, and the eligible/direction split."""

from __future__ import annotations

import pytest

from shared.constants import AUTONOMY_LADDER, MAX_RUNG, limit_of, rung_of
from shared.contracts import AgentContext, DriftResult
from shared.enums import AgentState, Direction, DriftSeverity
from shared.reason_codes import (
    AT_MAX_RUNG,
    CLAWBACK_CRITICAL_ERROR,
    CLAWBACK_DRIFT,
    CLAWBACK_RECOVERY_PENDING,
    COOLDOWN_ACTIVE,
    COOLDOWN_SATISFIED,
    DRIFT_ACTIVE,
    EVIDENCE_SUFFICIENT,
    INSUFFICIENT_SAMPLE,
    NO_DRIFT_DETECTED,
    NO_RECENT_CRITICAL_ERRORS,
    TRUST_BELOW_THRESHOLD,
)
from trust_engine.constants import (
    CLEAN_DECISIONS_AFTER_CLAWBACK,
    COOLDOWN_BETWEEN_INCREASES,
    MIN_SAMPLE_FOR_INCREASE,
    MIN_TRUST_SCORE_FOR_INCREASE,
)
from trust_engine.ladder import evaluate_ladder

NO_DRIFT = DriftResult()
WARNING_DRIFT = DriftResult(severity=DriftSeverity.WARNING, detected=True)
CONFIRMED_DRIFT = DriftResult(severity=DriftSeverity.CONFIRMED, detected=True)
CRITICAL_DRIFT = DriftResult(severity=DriftSeverity.CRITICAL, detected=True)

GOOD_SCORE = MIN_TRUST_SCORE_FOR_INCREASE + 10
GOOD_SAMPLE = MIN_SAMPLE_FOR_INCREASE + 10


def ladder(
    trust_score=GOOD_SCORE,
    acted_decisions=GOOD_SAMPLE,
    drift=NO_DRIFT,
    current_limit=AUTONOMY_LADDER[0],
    decisions_since_last_change=COOLDOWN_BETWEEN_INCREASES,
    decisions_since_clawback=None,
    state=AgentState.ACTIVE,
):
    context = AgentContext(
        current_limit=current_limit,
        decisions_since_last_change=decisions_since_last_change,
        decisions_since_clawback=decisions_since_clawback,
        state=state,
    )
    return evaluate_ladder(trust_score, acted_decisions, drift, context)


# --- the happy path: everything clears, agent moves up one rung ---------------------


def test_all_gates_clear_recommends_exactly_one_rung_up():
    result = ladder(current_limit=1000)
    assert result.direction is Direction.INCREASE
    assert result.recommended_rung == rung_of(1000) + 1
    assert result.recommended_limit == limit_of(rung_of(1000) + 1)
    assert result.eligible_for_increase is True


def test_increase_never_skips_a_rung_regardless_of_evidence_strength():
    result = ladder(current_limit=500, trust_score=99.99, acted_decisions=10_000)
    assert result.recommended_rung == rung_of(500) + 1  # not further, however strong


def test_positive_codes_present_on_a_clean_increase():
    result = ladder(current_limit=1000)
    for code in (EVIDENCE_SUFFICIENT, NO_DRIFT_DETECTED, NO_RECENT_CRITICAL_ERRORS, COOLDOWN_SATISFIED):
        assert code in result.reason_codes


# --- the six increase gates, each isolated -------------------------------------------


def test_insufficient_sample_blocks_and_is_named():
    result = ladder(acted_decisions=MIN_SAMPLE_FOR_INCREASE - 1)
    assert result.direction is Direction.HOLD
    assert result.eligible_for_increase is False
    assert INSUFFICIENT_SAMPLE in result.reason_codes


def test_trust_below_threshold_blocks_and_is_named():
    result = ladder(trust_score=MIN_TRUST_SCORE_FOR_INCREASE - 0.01)
    assert result.direction is Direction.HOLD
    assert result.eligible_for_increase is False
    assert TRUST_BELOW_THRESHOLD in result.reason_codes


def test_at_max_rung_blocks_and_is_named():
    result = ladder(current_limit=AUTONOMY_LADDER[MAX_RUNG])
    assert result.direction is Direction.HOLD
    assert result.eligible_for_increase is False
    assert AT_MAX_RUNG in result.reason_codes
    assert result.recommended_rung == MAX_RUNG  # stays capped, doesn't wrap


def test_active_drift_warning_blocks_evidence_even_though_not_a_clawback():
    result = ladder(drift=WARNING_DRIFT)
    assert result.direction is Direction.HOLD
    assert result.eligible_for_increase is False
    assert DRIFT_ACTIVE in result.reason_codes


# --- the eligible/direction split: the invariant we caught from the contract --------


def test_cooldown_active_leaves_eligible_true_but_direction_hold():
    """The core distinction: evidence supports it, but the wait isn't over.
    eligible_for_increase must stay True even though nothing is applied."""
    result = ladder(decisions_since_last_change=COOLDOWN_BETWEEN_INCREASES - 1)
    assert result.eligible_for_increase is True
    assert result.direction is Direction.HOLD
    assert COOLDOWN_ACTIVE in result.reason_codes


def test_cooldown_active_still_carries_the_positive_evidence_codes():
    result = ladder(decisions_since_last_change=COOLDOWN_BETWEEN_INCREASES - 1)
    for code in (EVIDENCE_SUFFICIENT, NO_DRIFT_DETECTED, NO_RECENT_CRITICAL_ERRORS):
        assert code in result.reason_codes
    assert COOLDOWN_SATISFIED not in result.reason_codes


def test_clawback_recovery_pending_leaves_eligible_true_but_direction_hold():
    result = ladder(
        decisions_since_clawback=CLEAN_DECISIONS_AFTER_CLAWBACK - 1,
    )
    assert result.eligible_for_increase is True
    assert result.direction is Direction.HOLD
    assert CLAWBACK_RECOVERY_PENDING in result.reason_codes


def test_recovery_satisfied_allows_increase():
    result = ladder(current_limit=1000, decisions_since_clawback=CLEAN_DECISIONS_AFTER_CLAWBACK)
    assert result.direction is Direction.INCREASE


def test_no_prior_clawback_never_blocks_on_recovery():
    """decisions_since_clawback=None means 'never clawed back' -- must not be
    treated as 0 and accidentally fail the recovery gate."""
    result = ladder(current_limit=1000, decisions_since_clawback=None)
    assert result.direction is Direction.INCREASE


# --- clawbacks -------------------------------------------------------------------------


def test_confirmed_drift_drops_exactly_one_rung():
    result = ladder(current_limit=2500, drift=CONFIRMED_DRIFT)
    assert result.direction is Direction.CLAWBACK
    assert result.recommended_rung == rung_of(2500) - 1
    assert result.eligible_for_increase is False
    assert CLAWBACK_DRIFT in result.reason_codes


def test_critical_drift_drops_exactly_one_rung_and_uses_the_critical_code():
    result = ladder(current_limit=2500, drift=CRITICAL_DRIFT)
    assert result.direction is Direction.CLAWBACK
    assert result.recommended_rung == rung_of(2500) - 1
    assert CLAWBACK_CRITICAL_ERROR in result.reason_codes


def test_clawback_never_drops_below_the_floor():
    result = ladder(current_limit=AUTONOMY_LADDER[0], drift=CRITICAL_DRIFT)
    assert result.recommended_rung == 0
    assert result.recommended_limit == AUTONOMY_LADDER[0]


def test_clawback_overrides_an_otherwise_perfect_increase():
    """Even with every increase gate cleared, a clawback wins -- checked first,
    unconditionally."""
    result = ladder(
        trust_score=99.9, acted_decisions=10_000,
        decisions_since_last_change=10_000,
        drift=CONFIRMED_DRIFT,
    )
    assert result.direction is Direction.CLAWBACK


def test_clawback_needs_no_cooldown_of_its_own():
    result = ladder(decisions_since_last_change=0, drift=CRITICAL_DRIFT)
    assert result.direction is Direction.CLAWBACK


# --- every recommended limit is always a real rung on the ladder -------------------


@pytest.mark.parametrize("limit", AUTONOMY_LADDER)
@pytest.mark.parametrize("drift", [NO_DRIFT, WARNING_DRIFT, CONFIRMED_DRIFT, CRITICAL_DRIFT])
def test_recommended_limit_is_always_a_valid_rung(limit, drift):
    result = ladder(current_limit=limit, drift=drift)
    assert result.recommended_limit in AUTONOMY_LADDER
    assert rung_of(result.recommended_limit) == result.recommended_rung