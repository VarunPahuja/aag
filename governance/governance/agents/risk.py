"""Risk Agent — financial exposure.

The question this agent answers: if we grant the proposed limit and the agent then
starts making mistakes, how much money is on the line before anyone notices?
"""

from __future__ import annotations

from shared.constants import CURRENCY
from shared.contracts import AgentOpinion, TrustEvaluation
from shared.enums import Direction, OpinionVerdict

from governance.agents.base import clamp_confidence, require_stub_mode

NAME = "risk"


def opine(evaluation: TrustEvaluation, mode: str) -> AgentOpinion:
    require_stub_mode(mode, NAME)

    concerns: list[str] = []

    # Exposure is the proposed ceiling itself: the most a single bad APPROVE can move.
    exposure = evaluation.recommended_limit
    recent_criticals = evaluation.critical_errors_in_recent_window

    if evaluation.direction is Direction.CLAWBACK:
        # Less authority is strictly less exposure. There is no risk-side argument
        # against a clawback, so this agent does not manufacture one.
        return AgentOpinion(
            agent_name=NAME,
            verdict=OpinionVerdict.CONCUR,
            reasoning=(
                f"Clawback reduces the ceiling from {CURRENCY} {evaluation.current_limit} to "
                f"{CURRENCY} {evaluation.recommended_limit}, cutting single-decision exposure. "
                f"No risk-side objection to reducing authority."
            ),
            concerns=(),
            confidence=0.9,
        )

    if evaluation.direction is Direction.HOLD:
        return AgentOpinion(
            agent_name=NAME,
            verdict=OpinionVerdict.ABSTAIN,
            reasoning=(
                f"No change proposed; exposure stays at {CURRENCY} {evaluation.current_limit}. "
                f"Nothing for this agent to weigh."
            ),
            concerns=(),
            confidence=0.5,
        )

    # --- direction is INCREASE from here ---

    if recent_criticals > 0:
        concerns.append(
            f"{recent_criticals} critical error(s) in the recent window, each one an "
            f"APPROVE that should have been a REJECT"
        )

    # A jump from 500 to 1000 doubles exposure; 5000 to 10000 also doubles it but puts
    # five times as much on a single decision. Both facts belong in the opinion.
    multiplier = exposure / evaluation.current_limit if evaluation.current_limit else 0.0
    if multiplier >= 2.0:
        concerns.append(
            f"proposed ceiling is {multiplier:.1f}x the current one "
            f"({CURRENCY} {evaluation.current_limit} to {CURRENCY} {exposure})"
        )

    if evaluation.critical_error_rate > 0.0:
        concerns.append(
            f"lifetime critical-error rate is {evaluation.critical_error_rate:.1%}, "
            f"applied against a larger ceiling from here on"
        )

    verdict = OpinionVerdict.OBJECT if recent_criticals > 0 else OpinionVerdict.CONCUR
    reasoning = (
        f"Raising the ceiling to {CURRENCY} {exposure} puts that much on any single "
        f"autonomous APPROVE. "
    )
    reasoning += (
        "Recent critical errors mean the blast radius should not grow yet."
        if recent_criticals > 0
        else f"No critical errors in the recent window; {evaluation.critical_errors} lifetime."
    )

    return AgentOpinion(
        agent_name=NAME,
        verdict=verdict,
        reasoning=reasoning,
        concerns=tuple(concerns),
        confidence=clamp_confidence(0.55 if recent_criticals else 0.8),
    )
