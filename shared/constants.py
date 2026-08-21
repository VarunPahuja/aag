"""Cross-lane constants. TREATY FILE — changes require all four reviewers.

ONLY put a constant here if more than one lane needs it. The Trust Engine's own tunables
(confidence level, window sizes, score weights) do NOT live here — they live in
trust/trust_engine/constants.py, because they change during week-3 tuning and a
four-person approval for every threshold experiment would stop that work dead.
"""

from __future__ import annotations

from typing import Final

SCHEMA_VERSION: Final[str] = "1.0"

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