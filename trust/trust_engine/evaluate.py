"""The orchestrator. The ONLY function the backend calls.

    evaluate(decisions, context) -> TrustEvaluation

Runs every statistic, then the ladder, then assembles the complete contract.
Pure: same decisions + same context always produce the same TrustEvaluation.
"""

from __future__ import annotations

from collections.abc import Sequence

from shared.constants import rung_of
from shared.contracts import AgentContext, DecisionRecord, TrustEvaluation

from trust_engine.ladder import evaluate_ladder
from trust_engine.score import compute_trust_score
from trust_engine.stats.drift import critical_errors_in_window, detect_drift
from trust_engine.stats.rates import (
    accuracy,
    error_breakdown,
    human_agreement,
    partition,
    utilization,
)


def evaluate(decisions: Sequence[DecisionRecord], context: AgentContext) -> TrustEvaluation:
    decisions = list(decisions)
    parts = partition(decisions)

    acc = accuracy(decisions)
    agree = human_agreement(decisions)
    util = utilization(decisions)
    errors = error_breakdown(decisions)
    drift = detect_drift(decisions)

    trust_score, components, weights_renormalised, score_reasons = compute_trust_score(
        accuracy=acc, human_agreement=agree, utilization=util,
        critical_errors=errors.critical,
    )

    ladder = evaluate_ladder(
        trust_score=trust_score,
        acted_decisions=len(parts.acted),
        drift=drift,
        context=context,
    )

    # current_rung is ALWAYS derived from current_limit, never passed
    # separately, so this can never actually disagree — the assert documents
    # the invariant the contract requires rather than guarding a real failure
    # mode here.
    current_rung = rung_of(context.current_limit)
    assert rung_of(context.current_limit) == current_rung
    assert rung_of(ladder.recommended_limit) == ladder.recommended_rung

    return TrustEvaluation(
        agent_id=decisions[0].agent_id if decisions else "unknown",
        total_decisions=parts.n_total,
        acted_decisions=len(parts.acted),
        escalated_decisions=len(parts.escalated),
        ruled_escalations=len(parts.ruled_escalations),
        accuracy=acc,
        human_agreement=agree,
        utilization=util,
        critical_errors=errors.critical,
        noncritical_errors=errors.noncritical,
        critical_error_rate=errors.critical_rate,
        critical_errors_in_recent_window=critical_errors_in_window(decisions),
        trust_score=trust_score,
        components=components,
        weights_renormalised=weights_renormalised,
        drift=drift,
        current_limit=context.current_limit,
        recommended_limit=ladder.recommended_limit,
        current_rung=current_rung,
        recommended_rung=ladder.recommended_rung,
        direction=ladder.direction,
        state=context.state,
        eligible_for_increase=ladder.eligible_for_increase,
        decisions_since_last_change=context.decisions_since_last_change,
        reason_codes=tuple(dict.fromkeys(score_reasons + ladder.reason_codes)),
    )