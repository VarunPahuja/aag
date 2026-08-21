"""Machine-readable reasons attached to every evaluation. TREATY FILE.

Why these exist: the backend renders them, the frontend styles them, and governance
agents read them. A free-text sentence cannot be any of those things reliably. The
human-readable sentence is generated FROM these codes, never the other way round.

Rule: append-only. Renaming a code silently breaks whatever reads it.
"""

from __future__ import annotations

from typing import Final

# --- why an increase was blocked ---------------------------------------------------
INSUFFICIENT_SAMPLE: Final = "INSUFFICIENT_SAMPLE"
COOLDOWN_ACTIVE: Final = "COOLDOWN_ACTIVE"
TRUST_BELOW_THRESHOLD: Final = "TRUST_BELOW_THRESHOLD"
AT_MAX_RUNG: Final = "AT_MAX_RUNG"
DRIFT_ACTIVE: Final = "DRIFT_ACTIVE"
CLAWBACK_RECOVERY_PENDING: Final = "CLAWBACK_RECOVERY_PENDING"

# --- why an increase was allowed ----------------------------------------------------
EVIDENCE_SUFFICIENT: Final = "EVIDENCE_SUFFICIENT"
NO_DRIFT_DETECTED: Final = "NO_DRIFT_DETECTED"
NO_RECENT_CRITICAL_ERRORS: Final = "NO_RECENT_CRITICAL_ERRORS"
COOLDOWN_SATISFIED: Final = "COOLDOWN_SATISFIED"

# --- why autonomy was reduced --------------------------------------------------------
CLAWBACK_DRIFT: Final = "CLAWBACK_DRIFT"
CLAWBACK_CRITICAL_ERROR: Final = "CLAWBACK_CRITICAL_ERROR"

# --- evidence quality notes -----------------------------------------------------------
NO_ACTED_DECISIONS: Final = "NO_ACTED_DECISIONS"
AGREEMENT_EVIDENCE_INSUFFICIENT: Final = "AGREEMENT_EVIDENCE_INSUFFICIENT"
WEIGHTS_RENORMALISED: Final = "WEIGHTS_RENORMALISED"
SAMPLE_EVIDENCE_INSUFFICIENT: Final = "SAMPLE_EVIDENCE_INSUFFICIENT"
RECOMMENDATION_CLAMPED: Final = "RECOMMENDATION_CLAMPED"

# --- audit sample findings --------------------------------------------------------------
SAMPLE_REVIEW_DISAGREEMENT: Final = "SAMPLE_REVIEW_DISAGREEMENT"

HUMAN_READABLE: Final[dict[str, str]] = {
    INSUFFICIENT_SAMPLE: "Not enough acted decisions yet to support an increase.",
    COOLDOWN_ACTIVE: "Too few decisions since the last autonomy change.",
    TRUST_BELOW_THRESHOLD: "Trust score is below the threshold for the next rung.",
    AT_MAX_RUNG: "Already at the highest autonomy rung.",
    DRIFT_ACTIVE: "Recent performance has degraded against the historical baseline.",
    CLAWBACK_RECOVERY_PENDING: "Not enough clean decisions since the last clawback.",
    EVIDENCE_SUFFICIENT: "Sample size and confidence bound both clear the gate.",
    NO_DRIFT_DETECTED: "Recent performance matches the historical baseline.",
    NO_RECENT_CRITICAL_ERRORS: "No critical errors in the recent window.",
    COOLDOWN_SATISFIED: "Enough decisions have elapsed since the last change.",
    CLAWBACK_DRIFT: "Autonomy reduced one rung after confirmed performance drift.",
    CLAWBACK_CRITICAL_ERROR: "Autonomy reset to the floor after a critical error.",
    NO_ACTED_DECISIONS: "The agent has escalated everything and decided nothing.",
    AGREEMENT_EVIDENCE_INSUFFICIENT: "Too few human-ruled escalations to score agreement.",
    WEIGHTS_RENORMALISED: "Score computed over available components only.",
    SAMPLE_EVIDENCE_INSUFFICIENT: "Too few reviewed audit samples to support an accuracy estimate.",
    RECOMMENDATION_CLAMPED: "The proposed limit exceeded the hard ceiling and was reduced before reaching the agent.",
    SAMPLE_REVIEW_DISAGREEMENT: "A sampled review found the agent's action did not match the reviewer's verdict.",
}


def describe(codes: list[str]) -> str:
    """Turn a list of codes into one readable sentence."""
    return " ".join(HUMAN_READABLE.get(c, f"[{c}]") for c in codes)