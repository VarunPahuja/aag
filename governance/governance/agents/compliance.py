"""Compliance Agent — does the proposal violate a stated constraint?

Two kinds of check, both mechanical:

- **Policy gates** — reason codes the trust engine already attached that say an
  increase is blocked. The human-readable sentence comes from `describe()`, never
  hand-written here; that is the rule reason codes exist to enforce.
- **Contract invariants** — the rung/limit pairing and the `direction` vs.
  `eligible_for_increase` relationship documented on `TrustEvaluation`. A frozen
  dataclass cannot enforce its own invariants, so something has to check them, and a
  violation reaching the Policy Engine unremarked is exactly the silent cross-lane
  drift ADR-0005 is about.
"""

from __future__ import annotations

from shared.constants import AUTONOMY_LADDER, rung_of
from shared.contracts import AgentOpinion, TrustEvaluation
from shared.enums import AgentState, Direction, OpinionVerdict
from shared.reason_codes import (
    AT_MAX_RUNG,
    CLAWBACK_RECOVERY_PENDING,
    COOLDOWN_ACTIVE,
    DRIFT_ACTIVE,
    INSUFFICIENT_SAMPLE,
    TRUST_BELOW_THRESHOLD,
    describe,
)

from governance.agents.base import require_stub_mode

NAME = "compliance"

BLOCKING_CODES = (
    INSUFFICIENT_SAMPLE,
    COOLDOWN_ACTIVE,
    TRUST_BELOW_THRESHOLD,
    AT_MAX_RUNG,
    DRIFT_ACTIVE,
    CLAWBACK_RECOVERY_PENDING,
)

# An agent that is restricted or suspended has had its authority curtailed for cause.
# Proposing to widen it is a contradiction regardless of what the numbers say.
NON_INCREASABLE_STATES = (AgentState.RESTRICTED, AgentState.SUSPENDED)


def opine(evaluation: TrustEvaluation, mode: str) -> AgentOpinion:
    require_stub_mode(mode, NAME)

    violations: list[str] = []

    if evaluation.recommended_limit not in AUTONOMY_LADDER:
        violations.append(
            f"proposed limit {evaluation.recommended_limit} is not a rung on the "
            f"autonomy ladder {AUTONOMY_LADDER}"
        )

    # Documented invariant on TrustEvaluation: rung_of(limit) == rung, for both pairs.
    if rung_of(evaluation.recommended_limit) != evaluation.recommended_rung:
        violations.append(
            f"recommended_limit {evaluation.recommended_limit} maps to rung "
            f"{rung_of(evaluation.recommended_limit)}, but recommended_rung says "
            f"{evaluation.recommended_rung}"
        )
    if rung_of(evaluation.current_limit) != evaluation.current_rung:
        violations.append(
            f"current_limit {evaluation.current_limit} maps to rung "
            f"{rung_of(evaluation.current_limit)}, but current_rung says "
            f"{evaluation.current_rung}"
        )

    if evaluation.direction is Direction.INCREASE:
        # The reverse does not hold — eligible + HOLD is a legal state (cooldown). Only
        # this direction implies eligibility.
        if not evaluation.eligible_for_increase:
            violations.append(
                "direction is INCREASE but eligible_for_increase is False, which the "
                "TrustEvaluation contract forbids"
            )
        if evaluation.state in NON_INCREASABLE_STATES:
            violations.append(
                f"agent state is {evaluation.state.value}; autonomy cannot be widened "
                f"while its authority is curtailed"
            )

    blocking = tuple(c for c in evaluation.reason_codes if c in BLOCKING_CODES)
    if evaluation.direction is Direction.INCREASE and blocking:
        return AgentOpinion(
            agent_name=NAME,
            verdict=OpinionVerdict.OBJECT,
            reasoning=(
                f"An increase is proposed while {len(blocking)} blocking condition(s) "
                f"are attached to the evaluation: {describe(list(blocking))}"
            ),
            concerns=tuple(violations) + blocking,
            confidence=0.95,
        )

    if violations:
        return AgentOpinion(
            agent_name=NAME,
            verdict=OpinionVerdict.OBJECT,
            reasoning=(
                f"The evaluation violates {len(violations)} stated constraint(s) before "
                f"any judgment about the agent's performance is reached."
            ),
            concerns=tuple(violations),
            confidence=0.95,
        )

    if evaluation.direction is Direction.HOLD:
        return AgentOpinion(
            agent_name=NAME,
            verdict=OpinionVerdict.ABSTAIN,
            reasoning=(
                "No autonomy change proposed, so no constraint is engaged. "
                f"Evaluation reason codes: {describe(list(evaluation.reason_codes)) or 'none'}"
            ),
            concerns=(),
            confidence=0.6,
        )

    return AgentOpinion(
        agent_name=NAME,
        verdict=OpinionVerdict.CONCUR,
        reasoning=(
            f"Proposal is on-ladder at {evaluation.recommended_limit} (rung "
            f"{evaluation.recommended_rung}), rung/limit pairs are consistent, and no "
            f"blocking reason code is attached. "
            f"{describe(list(evaluation.reason_codes))}"
        ),
        concerns=(),
        confidence=0.85,
    )
