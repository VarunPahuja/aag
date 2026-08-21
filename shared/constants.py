"""Cross-lane constants. TREATY FILE — changes require all four reviewers.

ONLY put a constant here if more than one lane needs it. The Trust Engine's own tunables
(confidence level, window sizes, score weights) do NOT live here — they live in
trust/trust_engine/constants.py, because they change during week-3 tuning and a
four-person approval for every threshold experiment would stop that work dead.
"""

from __future__ import annotations

from typing import Final

SCHEMA_VERSION: Final[str] = "1.1"

# --- money -----------------------------------------------------------------------
CURRENCY: Final[str] = "INR"

# --- the autonomy ladder -----------------------------------------------------------
# Shared because the Policy Engine enforces these limits, the frontend displays them,
# and the simulator generates invoice amounts around them. All four must agree exactly.
AUTONOMY_LADDER: Final[tuple[int, ...]] = (500, 1000, 2500, 5000, 10000)
AUTONOMY_FLOOR: Final[int] = AUTONOMY_LADDER[0]
MAX_RUNG: Final[int] = len(AUTONOMY_LADDER) - 1

# --- trust score scale ---------------------------------------------------------------
TRUST_SCORE_MIN: Final[float] = 0.0
TRUST_SCORE_MAX: Final[float] = 100.0

# --- the definition everyone must agree on --------------------------------------------
CRITICAL_ERROR_DEFINITION: Final[str] = (
    "The agent APPROVED an invoice whose ground truth is REJECT. Money leaves the "
    "building. Rejecting a valid invoice is an error but NOT a critical one."
)


def rung_of(limit: int) -> int:
    """Which rung (0-4) does this rupee amount correspond to?"""
    rung = 0
    for i, value in enumerate(AUTONOMY_LADDER):
        if limit >= value:
            rung = i
    return rung


def limit_of(rung: int) -> int:
    """The rupee amount for a given rung, clamped to a valid rung."""
    return AUTONOMY_LADDER[max(0, min(rung, MAX_RUNG))]


# --- audit sampling --------------------------------------------------------------
# An agent on the floor rung has every autonomous approval reviewed by a human; a
# highly trusted agent at the top rung has only 5% reviewed. The shrinking review
# burden as trust increases IS the system's ROI — earning autonomy means earning
# less oversight, not just a higher rupee ceiling. These sampled reviews are also
# the ground-truth source for accuracy once the system is running past the
# simulator, where (unlike DecisionRecord.ground_truth today) no deterministic
# correct answer exists to fall back on.
SAMPLING_RATE_BY_RUNG: Final[tuple[float, ...]] = (1.0, 0.50, 0.25, 0.10, 0.05)

# A rate is not a count. 5% of a low-volume agent's decisions can still be too few
# reviewed samples to say anything — this is the floor on *reviewed* samples before
# a sample-derived accuracy estimate is trusted, independent of the rate that
# produced them.
MIN_SAMPLES_FOR_ACCURACY_ESTIMATE: Final[int] = 20


def sampling_rate_of(rung: int) -> float:
    """The review-sampling rate for a given rung, clamped to a valid rung."""
    return SAMPLING_RATE_BY_RUNG[max(0, min(rung, MAX_RUNG))]