"""Recommendation fixtures — built as real `shared.contracts.Recommendation`
and `AgentOpinion` instances (see `app/fixtures/trust.py` for why).

Two recommendations, matching `app/fixtures/trust.py`'s story:

- **agent-01** — INCREASE, still `PENDING` human authorization (ADR-0004).
  Demonstrates the hard ceiling: governance's own panel reasoned its way to
  rung 4 headroom, but the backend clamps `proposed_limit` to what
  `TrustEvaluation.recommended_limit` actually supports (rung 3) before the
  recommendation is even shown to a human — `clamped`/`clamped_from` make
  that visible in the response, not just in a log line.
- **agent-03** — CLAWBACK, already `APPROVED` (a clawback needs no human
  sign-off, ADR-0004) and applied — matches `app/fixtures/policy_versions.py`'s
  `pv-agent03-004` row.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from shared.constants import limit_of
from shared.contracts import AgentOpinion, Recommendation
from shared.enums import Direction, OpinionVerdict, RecommendationStatus

from app.schemas.governance import RecommendationOut

_NOW = datetime(2026, 8, 27, 12, 0, tzinfo=UTC)

_agent01_opinions = (
    AgentOpinion(
        agent_name="risk", verdict=OpinionVerdict.CONCUR,
        reasoning="Exposure roughly doubles at rung 3, but zero critical errors in "
        "the recent window and a lifetime rate under 1%. Acceptable increase.",
        concerns=(), confidence=0.82,
    ),
    AgentOpinion(
        agent_name="performance", verdict=OpinionVerdict.CONCUR,
        reasoning="Wilson lower bound on accuracy is 0.887 over 150 acted decisions — "
        "comfortably above the trust-score threshold, and improving, not flat.",
        concerns=(), confidence=0.88,
    ),
    AgentOpinion(
        agent_name="compliance", verdict=OpinionVerdict.CONCUR,
        reasoning="Human agreement (0.875, n=8) is thin but directionally positive; "
        "no policy exceptions raised for this agent.",
        concerns=("Human-agreement sample size is small; revisit at the next evaluation.",),
        confidence=0.65,
    ),
    AgentOpinion(
        agent_name="audit", verdict=OpinionVerdict.CONCUR,
        reasoning="No drift detected, no recent critical errors, cooldown satisfied. "
        "Nothing in the decision log warrants holding this increase.",
        concerns=(), confidence=0.80,
    ),
)

RECOMMENDATION_AGENT_01 = Recommendation(
    recommendation_id="rec-agent01-001",
    agent_id="agent-01",
    direction=Direction.INCREASE,
    proposed_limit=limit_of(3),  # the ceiling the evidence actually supports
    proposed_rung=3,
    rationale=(
        "Trust score 82.4. The trust engine proposes increase; governance forwards "
        "increase. Panel: 4 concur, 0 object, 0 abstain. No agent objected. The "
        "panel's own headroom read rung 4, but the backend's hard ceiling clamped "
        "the ask to rung 3 (the trust engine's evidence-supported limit) before "
        "this recommendation reached a human. Requires human authorization before "
        "any limit changes."
    ),
    opinions=_agent01_opinions,
    has_dissent=False,
    confidence=round(sum(o.confidence for o in _agent01_opinions) / len(_agent01_opinions), 4),
    governance_mode="stub",
    status=RecommendationStatus.PENDING,
    trust_evaluation_ref="trust-eval-agent01-002",
    generated_at=_NOW,
    clamped=True,
    clamped_from=limit_of(4),
)

_agent03_opinions = (
    AgentOpinion(
        agent_name="risk", verdict=OpinionVerdict.CONCUR,
        reasoning="Clawback reduces the ceiling from 2,500 to 1,000, cutting single-decision "
        "exposure. No risk-side objection to reducing authority.",
        concerns=(), confidence=0.90,
    ),
    AgentOpinion(
        agent_name="performance", verdict=OpinionVerdict.CONCUR,
        reasoning="Recent accuracy dropped to 0.80 against a 0.94 baseline, z=3.21, p=0.0013 — "
        "a confirmed, not just tripwire-level, drop.",
        concerns=(), confidence=0.91,
    ),
    AgentOpinion(
        agent_name="compliance", verdict=OpinionVerdict.OBJECT,
        reasoning="Three critical errors in the recent window is itself grounds for review "
        "independent of the statistical drift finding.",
        concerns=(
            (
                "Recommend a manual audit-sample pass over agent-03's last 20 decisions "
                "once recovery decisions accumulate."
            ),
        ),
        confidence=0.77,
    ),
    AgentOpinion(
        agent_name="audit", verdict=OpinionVerdict.CONCUR,
        reasoning="Drift severity CONFIRMED per the two-stage detector; this is exactly "
        "the case ADR-0006 exists to catch before it compounds.",
        concerns=(), confidence=0.85,
    ),
)

RECOMMENDATION_AGENT_03 = Recommendation(
    recommendation_id="rec-agent03-001",
    agent_id="agent-03",
    direction=Direction.CLAWBACK,
    proposed_limit=limit_of(1),
    proposed_rung=1,
    rationale=(
        "Trust score 41.2. The trust engine proposes clawback; governance forwards "
        "clawback. Panel: 3 concur, 1 object, 0 abstain. Dissent from compliance, "
        "which holds the proposal at its current limit. [compliance] Three critical "
        "errors in the recent window is itself grounds for review independent of "
        "the statistical drift finding. Clawback applied automatically; no human "
        "authorization required (ADR-0004)."
    ),
    opinions=_agent03_opinions,
    has_dissent=True,
    confidence=round(sum(o.confidence for o in _agent03_opinions) / len(_agent03_opinions), 4),
    governance_mode="stub",
    status=RecommendationStatus.APPROVED,
    trust_evaluation_ref="trust-eval-agent03-002",
    generated_at=_NOW - timedelta(days=2),
    clamped=False,
    clamped_from=None,
)

RECOMMENDATIONS: list[RecommendationOut] = [
    RecommendationOut.model_validate(RECOMMENDATION_AGENT_01, from_attributes=True),
    RecommendationOut.model_validate(RECOMMENDATION_AGENT_03, from_attributes=True),
]

RECOMMENDATIONS_BY_ID: dict[str, RecommendationOut] = {
    r.recommendation_id: r for r in RECOMMENDATIONS
}
