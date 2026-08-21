"""Drift detection: has the agent got worse recently?

Lifetime accuracy hides degradation. An agent with 400 good decisions and 50 terrible
recent ones still shows ~89% overall — looks fine. Comparing RECENT performance against
an earlier BASELINE is the only way to see the collapse in time to react.

Two stages, on purpose:

  1. TRIPWIRE   recent accuracy is >= 10 percentage points below baseline.
                Fast, blunt, easy to explain. Fires as WARNING.
  2. CONFIRM    a two-proportion z-test says that gap is unlikely to be noise.
                Upgrades WARNING -> CONFIRMED.

Why both: over 50 decisions, a 10-point swing can easily be luck. The tripwire alone
would claw back autonomy from an agent that did nothing wrong. The z-test alone would be
harder to explain to a judge. Together you get a number anyone understands, plus a
statistical reason to believe it.

A critical error short-circuits everything: no statistics, immediate CRITICAL.
"""

from __future__ import annotations

import math

from shared.contracts import DecisionRecord, DriftResult
from shared.enums import DriftSeverity

from trust_engine.constants import (
    CRITICAL_ERROR_WINDOW,
    DRIFT_ACCURACY_DROP_PP,
    DRIFT_ALPHA,
    DRIFT_MIN_N_FOR_TEST,
    RECENT_WINDOW,
)


def split_history(
    decisions: list[DecisionRecord], window: int = RECENT_WINDOW
) -> tuple[list[DecisionRecord], list[DecisionRecord]]:
    """Split into (baseline, recent) by sequence number.

    `recent` is the last `window` decisions; `baseline` is everything before them. Too
    few decisions means everything is 'recent' and there is no baseline — correct,
    since you cannot detect a change without a 'before' to compare against.
    """
    ordered = sorted(decisions, key=lambda d: (d.sequence, d.decision_id))
    if len(ordered) <= window:
        return [], ordered
    return ordered[:-window], ordered[-window:]


def accuracy_counts(decisions: list[DecisionRecord]) -> tuple[int, int]:
    """(correct, acted). Escalations excluded, same rule as everywhere else."""
    acted = [d for d in decisions if d.is_acted]
    return sum(1 for d in acted if d.is_correct), len(acted)


def two_proportion_z(
    k_recent: int, n_recent: int, k_baseline: int, n_baseline: int
) -> tuple[float, float]:
    """Test whether two success rates genuinely differ. Returns (z, one_sided_p_value).

    A NEGATIVE z means recent is worse. The p-value is one-sided because an agent
    getting BETTER is not drift — it's progress, and flagging it would block the very
    thing the system is meant to reward.
    """
    if n_recent <= 0 or n_baseline <= 0:
        return 0.0, 1.0

    p_recent = k_recent / n_recent
    p_baseline = k_baseline / n_baseline
    p_pooled = (k_recent + k_baseline) / (n_recent + n_baseline)

    variance = p_pooled * (1.0 - p_pooled) * (1.0 / n_recent + 1.0 / n_baseline)
    if variance <= 0.0:
        return 0.0, 1.0

    z = (p_recent - p_baseline) / math.sqrt(variance)
    p_value = 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))
    return z, p_value


def critical_errors_in_window(
    decisions: list[DecisionRecord], window: int = CRITICAL_ERROR_WINDOW
) -> int:
    """Count critical errors among the last `window` ACTED decisions."""
    acted = sorted(
        (d for d in decisions if d.is_acted), key=lambda d: (d.sequence, d.decision_id)
    )
    return sum(1 for d in acted[-window:] if d.is_critical_error)


def detect_drift(
    decisions: list[DecisionRecord],
    recent_window: int = RECENT_WINDOW,
    drop_threshold_pp: float = DRIFT_ACCURACY_DROP_PP,
    min_n: int = DRIFT_MIN_N_FOR_TEST,
    alpha: float = DRIFT_ALPHA,
) -> DriftResult:
    """The whole detector. INPUT: decisions. OUTPUT: DriftResult."""
    criticals = critical_errors_in_window(decisions)
    baseline, recent = split_history(decisions, recent_window)

    k_recent, n_recent = accuracy_counts(recent)
    k_baseline, n_baseline = accuracy_counts(baseline)

    recent_acc = (k_recent / n_recent) if n_recent else None
    baseline_acc = (k_baseline / n_baseline) if n_baseline else None

    if criticals > 0:
        return DriftResult(
            severity=DriftSeverity.CRITICAL,
            detected=True,
            recent_accuracy=recent_acc,
            baseline_accuracy=baseline_acc,
            critical_errors_in_window=criticals,
            recent_n=n_recent,
            baseline_n=n_baseline,
        )

    if recent_acc is None or baseline_acc is None:
        return DriftResult(
            severity=DriftSeverity.NONE,
            recent_accuracy=recent_acc,
            baseline_accuracy=baseline_acc,
            recent_n=n_recent,
            baseline_n=n_baseline,
        )

    drop_pp = (baseline_acc - recent_acc) * 100.0

    if drop_pp < drop_threshold_pp:
        return DriftResult(
            severity=DriftSeverity.NONE,
            recent_accuracy=recent_acc,
            baseline_accuracy=baseline_acc,
            drop_pp=drop_pp,
            recent_n=n_recent,
            baseline_n=n_baseline,
        )

    z, p_value = two_proportion_z(k_recent, n_recent, k_baseline, n_baseline)
    underpowered = n_recent < min_n or n_baseline < min_n

    if underpowered:
        severity = DriftSeverity.WARNING
    elif p_value < alpha:
        severity = DriftSeverity.CONFIRMED
    else:
        severity = DriftSeverity.WARNING

    return DriftResult(
        severity=severity,
        detected=True,
        recent_accuracy=recent_acc,
        baseline_accuracy=baseline_acc,
        drop_pp=drop_pp,
        z_statistic=z,
        p_value=p_value,
        recent_n=n_recent,
        baseline_n=n_baseline,
        underpowered=underpowered,
    )