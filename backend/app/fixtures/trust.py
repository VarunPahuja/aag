"""Trust-evaluation fixtures — built as real `shared.contracts.TrustEvaluation`
instances, then converted to `TrustEvaluationOut`. Building the real
dataclass first (rather than hand-writing a dict shaped like one) means a
mismatch between this fixture and the actual contract fails loudly at
import time, not silently in a response body.

`TrustEvaluation` carries no identity field by design (see
`app/schemas/trust.py`); `id` is minted here, the way the real backend will
mint one at persistence time.
"""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime, timedelta

from shared.constants import limit_of
from shared.contracts import DriftResult, ProportionResult, ScoreComponent, TrustEvaluation
from shared.enums import AgentState, Direction, DriftSeverity
from shared.reason_codes import (
    AGREEMENT_EVIDENCE_INSUFFICIENT,
    CLAWBACK_DRIFT,
    CLAWBACK_RECOVERY_PENDING,
    COOLDOWN_SATISFIED,
    EVIDENCE_SUFFICIENT,
    INSUFFICIENT_SAMPLE,
    NO_DRIFT_DETECTED,
    NO_RECENT_CRITICAL_ERRORS,
    WEIGHTS_RENORMALISED,
)

from app.schemas.trust import TrustEvaluationOut

_NOW = datetime(2026, 8, 27, 12, 0, tzinfo=UTC)

# Score-component names, matching trust/trust_engine/score.py's constants exactly
# (ACCURACY / AGREEMENT / CRITICAL_PENALTY / UTILIZATION) so a fixture consumer
# sees the same vocabulary the real engine will eventually produce.
_ACCURACY = "accuracy_wilson_lower"
_AGREEMENT = "human_agreement"
_CRITICAL_PENALTY = "critical_error_penalty"
_UTILIZATION = "autonomy_utilization"


def _mint(evaluation: TrustEvaluation, eval_id: str) -> TrustEvaluationOut:
    return TrustEvaluationOut(id=eval_id, **dataclasses.asdict(evaluation))


# --- agent-01: mid-ladder, strong evidence, eligible and recommended for INCREASE ------

_agent01_current = TrustEvaluation(
    agent_id="agent-01",
    total_decisions=160,
    acted_decisions=150,
    escalated_decisions=10,
    ruled_escalations=8,
    accuracy=ProportionResult(successes=141, trials=150, point=0.94, wilson_lower=0.887, wilson_upper=0.969),
    human_agreement=ProportionResult(successes=7, trials=8, point=0.875, wilson_lower=0.529, wilson_upper=0.978),
    utilization=ProportionResult(successes=150, trials=160, point=0.9375, wilson_lower=0.887, wilson_upper=0.967),
    critical_errors=1,
    noncritical_errors=8,
    critical_error_rate=1 / 150,
    critical_errors_in_recent_window=0,
    trust_score=82.4,
    components=(
        ScoreComponent(_ACCURACY, 0.887, 0.50, 0.50, True),
        ScoreComponent(_AGREEMENT, 0.529, 0.25, 0.25, True),
        ScoreComponent(_CRITICAL_PENALTY, 0.967, 0.15, 0.15, True),
        ScoreComponent(_UTILIZATION, 0.9375, 0.10, 0.10, True),
    ),
    weights_renormalised=False,
    drift=DriftResult(
        severity=DriftSeverity.NONE, detected=False, recent_accuracy=0.95, baseline_accuracy=0.93,
        drop_pp=-2.0, z_statistic=0.40, p_value=0.69, critical_errors_in_window=0,
        recent_n=50, baseline_n=100, underpowered=False,
    ),
    current_limit=limit_of(2),
    recommended_limit=limit_of(3),
    current_rung=2,
    recommended_rung=3,
    direction=Direction.INCREASE,
    state=AgentState.ACTIVE,
    eligible_for_increase=True,
    decisions_since_last_change=120,
    reason_codes=(EVIDENCE_SUFFICIENT, NO_DRIFT_DETECTED, NO_RECENT_CRITICAL_ERRORS, COOLDOWN_SATISFIED),
    evaluated_at=_NOW,
    config_fingerprint="stub-v1.1",
)

_agent01_earlier = dataclasses.replace(
    _agent01_current,
    total_decisions=100,
    acted_decisions=92,
    escalated_decisions=8,
    ruled_escalations=5,
    trust_score=76.1,
    current_limit=limit_of(1),
    recommended_limit=limit_of(2),
    current_rung=1,
    recommended_rung=2,
    decisions_since_last_change=100,
    evaluated_at=_NOW - timedelta(days=10),
)

# --- agent-02: probation, small sample, not yet eligible --------------------------------

_agent02_current = TrustEvaluation(
    agent_id="agent-02",
    total_decisions=14,
    acted_decisions=12,
    escalated_decisions=2,
    ruled_escalations=1,
    accuracy=ProportionResult(successes=10, trials=12, point=0.833, wilson_lower=0.554, wilson_upper=0.955),
    human_agreement=ProportionResult(successes=1, trials=1, point=1.0, wilson_lower=0.207, wilson_upper=1.0),
    utilization=ProportionResult(successes=12, trials=14, point=0.857, wilson_lower=0.601, wilson_upper=0.960),
    critical_errors=0,
    noncritical_errors=2,
    critical_error_rate=0.0,
    critical_errors_in_recent_window=0,
    trust_score=58.0,
    components=(
        ScoreComponent(_ACCURACY, 0.554, 0.50, 0.667, True),
        # Below MIN_RULED_ESCALATIONS_FOR_AGREEMENT (trust/trust_engine/constants.py) - dropped.
        ScoreComponent(_AGREEMENT, None, 0.25, 0.0, False),
        ScoreComponent(_CRITICAL_PENALTY, 1.0, 0.15, 0.20, True),
        ScoreComponent(_UTILIZATION, 0.857, 0.10, 0.133, True),
    ),
    weights_renormalised=True,
    drift=DriftResult(
        severity=DriftSeverity.NONE, detected=False, recent_accuracy=None, baseline_accuracy=None,
        drop_pp=None, z_statistic=None, p_value=None, critical_errors_in_window=0,
        recent_n=12, baseline_n=0, underpowered=True,
    ),
    current_limit=limit_of(0),
    recommended_limit=limit_of(0),
    current_rung=0,
    recommended_rung=0,
    direction=Direction.HOLD,
    state=AgentState.PROBATION,
    eligible_for_increase=False,
    decisions_since_last_change=12,
    reason_codes=(INSUFFICIENT_SAMPLE, AGREEMENT_EVIDENCE_INSUFFICIENT, WEIGHTS_RENORMALISED),
    evaluated_at=_NOW,
    config_fingerprint="stub-v1.1",
)

_agent02_earlier = dataclasses.replace(
    _agent02_current,
    total_decisions=4,
    acted_decisions=3,
    escalated_decisions=1,
    ruled_escalations=0,
    trust_score=41.0,
    decisions_since_last_change=3,
    evaluated_at=_NOW - timedelta(days=3),
)

# --- agent-03: confirmed drift -> automatic clawback one rung down, now recovering -----

_agent03_triggering = TrustEvaluation(
    agent_id="agent-03",
    total_decisions=210,
    acted_decisions=195,
    escalated_decisions=15,
    ruled_escalations=12,
    accuracy=ProportionResult(successes=165, trials=195, point=0.846, wilson_lower=0.788, wilson_upper=0.891),
    human_agreement=ProportionResult(successes=9, trials=12, point=0.75, wilson_lower=0.469, wilson_upper=0.911),
    utilization=ProportionResult(successes=195, trials=210, point=0.929, wilson_lower=0.886, wilson_upper=0.957),
    critical_errors=4,
    noncritical_errors=11,
    critical_error_rate=4 / 195,
    critical_errors_in_recent_window=3,
    trust_score=41.2,
    components=(
        ScoreComponent(_ACCURACY, 0.788, 0.50, 0.50, True),
        ScoreComponent(_AGREEMENT, 0.469, 0.25, 0.25, True),
        ScoreComponent(_CRITICAL_PENALTY, 0.897, 0.15, 0.15, True),
        ScoreComponent(_UTILIZATION, 0.929, 0.10, 0.10, True),
    ),
    weights_renormalised=False,
    drift=DriftResult(
        severity=DriftSeverity.CONFIRMED, detected=True, recent_accuracy=0.80, baseline_accuracy=0.94,
        drop_pp=14.0, z_statistic=3.21, p_value=0.0013, critical_errors_in_window=3,
        recent_n=50, baseline_n=100, underpowered=False,
    ),
    current_limit=limit_of(2),
    recommended_limit=limit_of(1),
    current_rung=2,
    recommended_rung=1,
    direction=Direction.CLAWBACK,
    state=AgentState.RESTRICTED,
    eligible_for_increase=False,
    decisions_since_last_change=45,
    reason_codes=(CLAWBACK_DRIFT,),
    evaluated_at=_NOW - timedelta(days=2),
    config_fingerprint="stub-v1.1",
)

_agent03_healthy_before = dataclasses.replace(
    _agent03_triggering,
    total_decisions=160,
    acted_decisions=150,
    escalated_decisions=10,
    ruled_escalations=9,
    accuracy=ProportionResult(successes=141, trials=150, point=0.94, wilson_lower=0.887, wilson_upper=0.969),
    critical_errors=1,
    noncritical_errors=8,
    critical_error_rate=1 / 150,
    critical_errors_in_recent_window=0,
    trust_score=79.0,
    direction=Direction.HOLD,
    state=AgentState.ACTIVE,
    eligible_for_increase=False,  # cooling down after its last increase
    drift=DriftResult(severity=DriftSeverity.NONE, detected=False, recent_accuracy=0.94,
                       baseline_accuracy=0.93, drop_pp=-1.0, z_statistic=0.2, p_value=0.84,
                       critical_errors_in_window=0, recent_n=50, baseline_n=100, underpowered=False),
    reason_codes=(),
    evaluated_at=_NOW - timedelta(days=14),
)

_agent03_recovering = dataclasses.replace(
    _agent03_triggering,
    total_decisions=215,
    acted_decisions=200,
    escalated_decisions=15,
    ruled_escalations=13,
    accuracy=ProportionResult(successes=169, trials=200, point=0.845, wilson_lower=0.790, wilson_upper=0.888),
    critical_errors=4,
    noncritical_errors=11,
    critical_error_rate=4 / 200,
    critical_errors_in_recent_window=0,
    trust_score=52.0,
    current_limit=limit_of(1),
    recommended_limit=limit_of(1),
    current_rung=1,
    recommended_rung=1,
    direction=Direction.HOLD,
    eligible_for_increase=False,
    decisions_since_last_change=5,
    drift=DriftResult(severity=DriftSeverity.NONE, detected=False, recent_accuracy=0.86,
                       baseline_accuracy=0.85, drop_pp=-1.0, z_statistic=0.15, p_value=0.88,
                       critical_errors_in_window=0, recent_n=5, baseline_n=100, underpowered=True),
    reason_codes=(CLAWBACK_RECOVERY_PENDING,),
    evaluated_at=_NOW,
)

# --- public: history (oldest first) and "current" (most recent) per agent --------------

TRUST_HISTORY: dict[str, list[TrustEvaluationOut]] = {
    "agent-01": [
        _mint(_agent01_earlier, "trust-eval-agent01-001"),
        _mint(_agent01_current, "trust-eval-agent01-002"),
    ],
    "agent-02": [
        _mint(_agent02_earlier, "trust-eval-agent02-001"),
        _mint(_agent02_current, "trust-eval-agent02-002"),
    ],
    "agent-03": [
        _mint(_agent03_healthy_before, "trust-eval-agent03-001"),
        _mint(_agent03_triggering, "trust-eval-agent03-002"),
        _mint(_agent03_recovering, "trust-eval-agent03-003"),
    ],
}

TRUST_CURRENT: dict[str, TrustEvaluationOut] = {
    agent_id: history[-1] for agent_id, history in TRUST_HISTORY.items()
}
