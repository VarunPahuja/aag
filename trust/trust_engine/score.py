"""Trust score composition. Pure: metrics in, a number in [0, 100] out.

Returns a plain tuple, not a lane-local dataclass — TrustEvaluation
(shared/contracts.py) is the only public result shape for this lane now.
See docs/adr/0005 on why a second, incompatible shape for the same idea was a
real problem, not a style nit.

WEIGHT RENORMALISATION
-----------------------
A new agent has no human-ruled escalations, so the human-agreement component has no
evidence. Left at a fixed 25% weight scoring 0, its trust score would be capped at 75
before doing anything wrong.

So a component with no evidence is dropped and its weight redistributed across the
components that DO have evidence — but NOT all absences qualify. Accuracy and
utilization are the two BEHAVIOURAL axes (are you right? do you act?) and are NEVER
dropped once any decision exists — abstaining scores 0 on them rather than hiding from
them. Only human agreement and the critical penalty may be redistributed, because their
absence is genuinely uninformative.

CRITICAL-ERROR PENALTY
------------------------
The 5x weight applies HERE, and nowhere else — never inside the accuracy proportion,
which would invalidate the Wilson bound derived from it.
"""

from __future__ import annotations

from shared.contracts import ProportionResult, ScoreComponent
from shared.reason_codes import (
    AGREEMENT_EVIDENCE_INSUFFICIENT,
    NO_ACTED_DECISIONS,
    WEIGHTS_RENORMALISED,
)

from trust_engine.constants import (
    CRITICAL_ERROR_WEIGHT,
    MIN_RULED_ESCALATIONS_FOR_AGREEMENT,
    WEIGHT_CRITICAL_PENALTY,
    WEIGHT_HUMAN_AGREEMENT,
    WEIGHT_UTILIZATION,
    WEIGHT_WILSON_LOWER,
)

ACCURACY = "accuracy_wilson_lower"
AGREEMENT = "human_agreement"
CRITICAL_PENALTY = "critical_error_penalty"
UTILIZATION = "autonomy_utilization"


def critical_error_penalty(critical_errors: int, acted_total: int) -> float | None:
    """1.0 clean, 0.0 once the critical rate reaches 1/CRITICAL_ERROR_WEIGHT.
    None with no acted decisions — undecided is not the same as clean."""
    if acted_total <= 0:
        return None
    rate = critical_errors / acted_total
    return max(0.0, 1.0 - CRITICAL_ERROR_WEIGHT * rate)


def compute_trust_score(
    accuracy: ProportionResult,
    human_agreement: ProportionResult,
    utilization: ProportionResult,
    critical_errors: int,
) -> tuple[float, tuple[ScoreComponent, ...], bool, tuple[str, ...]]:
    """Returns (trust_score, components, weights_renormalised, reason_codes)."""
    acted_total = accuracy.trials
    has_any_decisions = utilization.trials > 0
    reasons: list[str] = []

    # Accuracy and utilization are the behavioural axes — never dropped once any
    # decision exists. Abstaining scores 0 on them rather than hiding from them.
    accuracy_available = has_any_decisions
    if acted_total == 0:
        reasons.append(NO_ACTED_DECISIONS)

    agreement_available = human_agreement.trials >= MIN_RULED_ESCALATIONS_FOR_AGREEMENT
    if not agreement_available:
        reasons.append(AGREEMENT_EVIDENCE_INSUFFICIENT)

    penalty = critical_error_penalty(critical_errors, acted_total)
    utilization_available = has_any_decisions

    raw = [
        (ACCURACY, accuracy.wilson_lower if accuracy_available else None,
         WEIGHT_WILSON_LOWER, accuracy_available),
        (AGREEMENT, human_agreement.wilson_lower if agreement_available else None,
         WEIGHT_HUMAN_AGREEMENT, agreement_available),
        (CRITICAL_PENALTY, penalty, WEIGHT_CRITICAL_PENALTY, penalty is not None),
        (UTILIZATION, utilization.point if utilization_available else None,
         WEIGHT_UTILIZATION, utilization_available),
    ]

    available_weight = sum(w for _, _, w, ok in raw if ok)
    weights_renormalised = bool(available_weight) and abs(available_weight - 1.0) > 1e-9
    if weights_renormalised:
        reasons.append(WEIGHTS_RENORMALISED)

    components: list[ScoreComponent] = []
    for name, value, nominal, ok in raw:
        effective = (nominal / available_weight) if (ok and available_weight) else 0.0
        components.append(
            ScoreComponent(
                name=name, value=value, nominal_weight=nominal,
                effective_weight=effective, available=ok,
            )
        )

    total = sum(c.contribution for c in components) if available_weight else 0.0
    trust_score = round(_clamp01(total) * 100.0, 4)

    return trust_score, tuple(components), weights_renormalised, tuple(reasons)


def _clamp01(x: float) -> float:
    import math
    if math.isnan(x):
        return 0.0
    return 0.0 if x < 0.0 else min(x, 1.0)