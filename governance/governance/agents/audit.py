"""Audit Agent — anomalies and gaps in the record.

Scope note, stated rather than papered over: this agent reasons over a
`TrustEvaluation`, which carries *aggregates* — counts, rates, proportions. Two of the
anomaly classes named in the lane brief (per-vendor patterns, per-decision error
clustering by time) need the underlying `DecisionRecord` history, which this contract
does not carry. What is detectable here is clustering in the recent window versus
lifetime, and holes in the evidence itself: escalations nobody ruled on, score
components that were unavailable, agreement evidence too thin to use.

Widening this agent's input beyond `TrustEvaluation` would be a cross-lane contract
change, so it gets an ADR before it gets code (CONTRIBUTING.md) — not a quiet extra
parameter.
"""

from __future__ import annotations

from shared.contracts import AgentOpinion, TrustEvaluation
from shared.enums import OpinionVerdict
from shared.reason_codes import (
    AGREEMENT_EVIDENCE_INSUFFICIENT,
    SAMPLE_EVIDENCE_INSUFFICIENT,
    WEIGHTS_RENORMALISED,
    describe,
)

from governance.agents.base import clamp_confidence, require_stub_mode

NAME = "audit"

EVIDENCE_GAP_CODES = (
    AGREEMENT_EVIDENCE_INSUFFICIENT,
    WEIGHTS_RENORMALISED,
    SAMPLE_EVIDENCE_INSUFFICIENT,
)


def opine(evaluation: TrustEvaluation, mode: str) -> AgentOpinion:
    require_stub_mode(mode, NAME)

    anomalies: list[str] = []

    # A record gap, not a performance problem: the agent escalated, and nobody ruled.
    # Those decisions have no outcome attached and cannot support any conclusion.
    unruled = evaluation.escalated_decisions - evaluation.ruled_escalations
    if unruled > 0:
        anomalies.append(
            f"{unruled} of {evaluation.escalated_decisions} escalations have no human "
            f"ruling recorded"
        )

    # Clustering: if every critical error the agent has ever made is in the recent
    # window, that is a deteriorating agent, not a stable one with an old blemish.
    recent = evaluation.critical_errors_in_recent_window
    lifetime = evaluation.critical_errors
    if recent > 0 and recent == lifetime:
        anomalies.append(
            f"all {lifetime} lifetime critical error(s) fall in the recent window — "
            f"errors are clustering, not fading"
        )
    elif recent > 0:
        anomalies.append(f"{recent} of {lifetime} lifetime critical errors are recent")

    if evaluation.weights_renormalised:
        unavailable = tuple(c.name for c in evaluation.components if not c.available)
        anomalies.append(
            f"trust score was computed over available components only; missing: "
            f"{', '.join(unavailable) if unavailable else 'unspecified'}"
        )

    gap_codes = tuple(c for c in evaluation.reason_codes if c in EVIDENCE_GAP_CODES)

    if evaluation.total_decisions == 0:
        return AgentOpinion(
            agent_name=NAME,
            verdict=OpinionVerdict.ABSTAIN,
            reasoning="No decision history on record. There is nothing to audit yet.",
            concerns=("empty decision history",),
            confidence=0.2,
        )

    if anomalies:
        return AgentOpinion(
            agent_name=NAME,
            verdict=OpinionVerdict.OBJECT,
            reasoning=(
                f"The record has {len(anomalies)} anomaly/anomalies across "
                f"{evaluation.total_decisions} decisions. "
                f"{describe(list(gap_codes)) if gap_codes else ''}".strip()
            ),
            concerns=tuple(anomalies) + gap_codes,
            confidence=clamp_confidence(0.6 + 0.1 * len(anomalies)),
        )

    return AgentOpinion(
        agent_name=NAME,
        verdict=OpinionVerdict.CONCUR,
        reasoning=(
            f"{evaluation.total_decisions} decisions on record "
            f"({evaluation.acted_decisions} acted, {evaluation.escalated_decisions} "
            f"escalated, all ruled). No error clustering and no gaps in the evidence."
        ),
        concerns=(),
        confidence=0.8,
    )
