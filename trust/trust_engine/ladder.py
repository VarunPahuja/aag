"""The autonomy ladder: what should the agent's limit become?

Two independent questions, deliberately kept separate — see TrustEvaluation's
own docstring in shared/contracts.py:

  eligible_for_increase   does the EVIDENCE support going up a rung?
                          (sample size, trust score, no drift, not at the ceiling)
  direction == INCREASE   is the increase actually being recommended RIGHT NOW?
                          (eligible_for_increase, AND the cooldown/recovery
                          wait has actually elapsed)

An agent can be eligible_for_increase=True with direction=HOLD: it has earned
the evidence, but a cooldown or post-clawback recovery period is still
running. That is a real, meaningful state, not a bug — read reason_codes, not
direction alone, to tell "not eligible" apart from "eligible but waiting."

Clawback is checked FIRST and unconditionally overrides any increase
evaluation. Confirmed statistical drift, or a critical error in the recent
window, both drop the agent exactly one rung — never below the floor — with
no human step and no cooldown of their own. Note DriftSeverity.CRITICAL is
itself defined (drift.py) as firing specifically because a critical error was
found in the window, so the two clawback reason codes map directly onto the
two severities that trigger one: CONFIRMED -> statistical drift,
CRITICAL -> a critical error.
"""

from __future__ import annotations

from dataclasses import dataclass

from shared.constants import MAX_RUNG, limit_of, rung_of
from shared.contracts import AgentContext, DriftResult
from shared.enums import Direction, DriftSeverity
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


@dataclass(frozen=True, slots=True)
class LadderResult:
    direction: Direction
    recommended_rung: int
    recommended_limit: int
    eligible_for_increase: bool
    reason_codes: tuple[str, ...]


def evaluate_ladder(
    trust_score: float,
    acted_decisions: int,
    drift: DriftResult,
    context: AgentContext,
) -> LadderResult:
    current_rung = rung_of(context.current_limit)

    # --- clawback: unconditional, checked before any increase logic --------
    if drift.severity is DriftSeverity.CRITICAL:
        new_rung = max(current_rung - 1, 0)
        return LadderResult(
            Direction.CLAWBACK, new_rung, limit_of(new_rung),
            False, (CLAWBACK_CRITICAL_ERROR,),
        )
    if drift.severity is DriftSeverity.CONFIRMED:
        new_rung = max(current_rung - 1, 0)
        return LadderResult(
            Direction.CLAWBACK, new_rung, limit_of(new_rung),
            False, (CLAWBACK_DRIFT,),
        )

    # --- evidence gates: determine eligible_for_increase ---------------------
    evidence_codes: list[str] = []
    evidence_ok = True

    if acted_decisions < MIN_SAMPLE_FOR_INCREASE:
        evidence_codes.append(INSUFFICIENT_SAMPLE)
        evidence_ok = False
    if trust_score < MIN_TRUST_SCORE_FOR_INCREASE:
        evidence_codes.append(TRUST_BELOW_THRESHOLD)
        evidence_ok = False
    if current_rung >= MAX_RUNG:
        evidence_codes.append(AT_MAX_RUNG)
        evidence_ok = False
    if drift.detected:  # WARNING-level drift blocks growth without clawing back
        evidence_codes.append(DRIFT_ACTIVE)
        evidence_ok = False

    if not evidence_ok:
        return LadderResult(
            Direction.HOLD, current_rung, context.current_limit,
            False, tuple(evidence_codes),
        )

    # --- cooldown gates: block DIRECTION only, never eligible_for_increase --
    cooldown_codes: list[str] = []
    cooldown_ok = True

    if context.decisions_since_last_change < COOLDOWN_BETWEEN_INCREASES:
        cooldown_codes.append(COOLDOWN_ACTIVE)
        cooldown_ok = False
    if (
        context.decisions_since_clawback is not None
        and context.decisions_since_clawback < CLEAN_DECISIONS_AFTER_CLAWBACK
    ):
        cooldown_codes.append(CLAWBACK_RECOVERY_PENDING)
        cooldown_ok = False

    positive_codes = [EVIDENCE_SUFFICIENT, NO_DRIFT_DETECTED, NO_RECENT_CRITICAL_ERRORS]

    if not cooldown_ok:
        return LadderResult(
            Direction.HOLD, current_rung, context.current_limit,
            True, tuple(positive_codes + cooldown_codes),
        )

    new_rung = min(current_rung + 1, MAX_RUNG)
    return LadderResult(
        Direction.INCREASE, new_rung, limit_of(new_rung),
        True, tuple(positive_codes + [COOLDOWN_SATISFIED]),
    )