"""Representative TrustEvaluations to reason over.

These are hand-built rather than produced by the trust engine on purpose: this lane must
stay testable without importing `trust/`, and `evaluate()` does not exist yet anyway
(due 26 Aug). They are shaped to match the contract, not to be statistically derived —
governance reads these numbers, it never checks their arithmetic.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from shared.constants import rung_of
from shared.contracts import DriftResult, ProportionResult, TrustEvaluation
from shared.enums import AgentState, Direction, DriftSeverity
from shared.reason_codes import (
    COOLDOWN_ACTIVE,
    DRIFT_ACTIVE,
    EVIDENCE_SUFFICIENT,
    NO_DRIFT_DETECTED,
    NO_RECENT_CRITICAL_ERRORS,
)


def make_evaluation(
    *,
    current_limit: int = 500,
    recommended_limit: int = 500,
    direction: Direction = Direction.HOLD,
    accuracy: ProportionResult | None = None,
    drift: DriftResult | None = None,
    critical_errors: int = 0,
    critical_errors_in_recent_window: int = 0,
    critical_error_rate: float = 0.0,
    total_decisions: int = 100,
    acted_decisions: int = 90,
    escalated_decisions: int = 10,
    ruled_escalations: int = 10,
    trust_score: float = 70.0,
    state: AgentState = AgentState.ACTIVE,
    eligible_for_increase: bool = False,
    reason_codes: tuple[str, ...] = (),
    weights_renormalised: bool = False,
) -> TrustEvaluation:
    """Build a contract-valid TrustEvaluation, keeping the rung/limit invariants intact."""
    return TrustEvaluation(
        agent_id="agent-01",
        total_decisions=total_decisions,
        acted_decisions=acted_decisions,
        escalated_decisions=escalated_decisions,
        ruled_escalations=ruled_escalations,
        accuracy=accuracy,
        drift=drift if drift is not None else DriftResult(),
        critical_errors=critical_errors,
        critical_errors_in_recent_window=critical_errors_in_recent_window,
        critical_error_rate=critical_error_rate,
        trust_score=trust_score,
        weights_renormalised=weights_renormalised,
        current_limit=current_limit,
        current_rung=rung_of(current_limit),
        recommended_limit=recommended_limit,
        recommended_rung=rung_of(recommended_limit),
        direction=direction,
        state=state,
        eligible_for_increase=eligible_for_increase,
        reason_codes=reason_codes,
        evaluated_at=datetime.now(UTC),
        config_fingerprint="test-fingerprint",
    )


@pytest.fixture
def healthy_increase() -> TrustEvaluation:
    """Strong evidence, tight interval, no drift — the case an increase should survive."""
    return make_evaluation(
        current_limit=500,
        recommended_limit=1000,
        direction=Direction.INCREASE,
        eligible_for_increase=True,
        accuracy=ProportionResult(
            successes=196, trials=200, point=0.98, wilson_lower=0.951, wilson_upper=0.993
        ),
        drift=DriftResult(severity=DriftSeverity.NONE, recent_accuracy=0.98, baseline_accuracy=0.97),
        total_decisions=220,
        acted_decisions=200,
        escalated_decisions=20,
        ruled_escalations=20,
        trust_score=88.0,
        reason_codes=(EVIDENCE_SUFFICIENT, NO_DRIFT_DETECTED, NO_RECENT_CRITICAL_ERRORS),
    )


@pytest.fixture
def thin_sample() -> TrustEvaluation:
    """10/10 correct. Looks perfect, proves little — the Wilson lower bound is the story."""
    return make_evaluation(
        current_limit=500,
        recommended_limit=1000,
        direction=Direction.INCREASE,
        eligible_for_increase=True,
        accuracy=ProportionResult(
            successes=10, trials=10, point=1.0, wilson_lower=0.722, wilson_upper=1.0
        ),
        drift=DriftResult(severity=DriftSeverity.NONE, underpowered=True),
        total_decisions=12,
        acted_decisions=10,
        escalated_decisions=2,
        ruled_escalations=2,
        trust_score=76.0,
        reason_codes=(NO_DRIFT_DETECTED,),
    )


@pytest.fixture
def active_drift() -> TrustEvaluation:
    """A measured, sustained accuracy drop — the clawback path."""
    return make_evaluation(
        current_limit=2500,
        recommended_limit=1000,
        direction=Direction.CLAWBACK,
        accuracy=ProportionResult(
            successes=170, trials=200, point=0.85, wilson_lower=0.794, wilson_upper=0.893
        ),
        drift=DriftResult(
            severity=DriftSeverity.CONFIRMED,
            detected=True,
            recent_accuracy=0.72,
            baseline_accuracy=0.94,
            drop_pp=22.0,
            z_statistic=-3.9,
            p_value=0.0001,
            recent_n=50,
            baseline_n=150,
        ),
        trust_score=41.0,
        reason_codes=(DRIFT_ACTIVE,),
    )


@pytest.fixture
def recent_critical_error() -> TrustEvaluation:
    """Money left the building recently, but an increase is still on the table."""
    return make_evaluation(
        current_limit=1000,
        recommended_limit=2500,
        direction=Direction.INCREASE,
        eligible_for_increase=True,
        accuracy=ProportionResult(
            successes=190, trials=200, point=0.95, wilson_lower=0.911, wilson_upper=0.972
        ),
        critical_errors=1,
        critical_errors_in_recent_window=1,
        critical_error_rate=0.005,
        trust_score=79.0,
        reason_codes=(EVIDENCE_SUFFICIENT,),
    )


@pytest.fixture
def blocked_by_cooldown() -> TrustEvaluation:
    """Eligible on the evidence, blocked by a cooldown — a legal eligible+HOLD state."""
    return make_evaluation(
        current_limit=1000,
        recommended_limit=1000,
        direction=Direction.HOLD,
        eligible_for_increase=True,
        accuracy=ProportionResult(
            successes=98, trials=100, point=0.98, wilson_lower=0.930, wilson_upper=0.995
        ),
        trust_score=85.0,
        reason_codes=(COOLDOWN_ACTIVE, EVIDENCE_SUFFICIENT),
    )


@pytest.fixture
def empty_history() -> TrustEvaluation:
    """A brand-new agent. No decisions, no evidence, nothing to reason about."""
    return make_evaluation(
        current_limit=500,
        recommended_limit=500,
        direction=Direction.HOLD,
        accuracy=None,
        total_decisions=0,
        acted_decisions=0,
        escalated_decisions=0,
        ruled_escalations=0,
        trust_score=0.0,
        state=AgentState.PROBATION,
    )
