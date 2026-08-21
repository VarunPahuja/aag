"""Trust Engine tunables. LANE-LOCAL — owned entirely by uk/trust.

These are deliberately NOT in shared/. They change during week-3 tuning against real
observed agent behavior, and a four-person review for every threshold experiment would
stop that work dead. Tuning means editing THIS file and re-running tests — never
editing logic elsewhere.
"""

from __future__ import annotations

from typing import Final

# --- confidence -----------------------------------------------------------------
Z_95: Final[float] = 1.96

# --- trust score weights (must sum to 1.0) ----------------------------------------
WEIGHT_WILSON_LOWER: Final[float] = 0.50
WEIGHT_HUMAN_AGREEMENT: Final[float] = 0.25
WEIGHT_CRITICAL_PENALTY: Final[float] = 0.15
WEIGHT_UTILIZATION: Final[float] = 0.10

# Human agreement needs at least this many ruled escalations before it counts —
# below this, its weight is redistributed to the other three components.
MIN_RULED_ESCALATIONS_FOR_AGREEMENT: Final[int] = 5

# --- evidence gates ---------------------------------------------------------------
MIN_SAMPLE_FOR_INCREASE: Final[int] = 30
MIN_TRUST_SCORE_FOR_INCREASE: Final[float] = 70.0
RECENT_WINDOW: Final[int] = 50
CRITICAL_ERROR_WINDOW: Final[int] = 20

# --- error weighting ---------------------------------------------------------------
# Applied ONLY inside the critical-error penalty component, never inside the accuracy
# proportion itself — weighting a binomial count would invalidate the Wilson bound.
CRITICAL_ERROR_WEIGHT: Final[float] = 5.0

# --- drift ---------------------------------------------------------------------------
DRIFT_ACCURACY_DROP_PP: Final[float] = 10.0
DRIFT_MIN_N_FOR_TEST: Final[int] = 30
DRIFT_ALPHA: Final[float] = 0.05

# --- cooldowns (measured in decisions, not wall-clock time) ------------------------
COOLDOWN_BETWEEN_INCREASES: Final[int] = 100
CLEAN_DECISIONS_AFTER_CLAWBACK: Final[int] = 75

# --- snapshots -----------------------------------------------------------------------
SNAPSHOT_EVERY_N_DECISIONS: Final[int] = 10