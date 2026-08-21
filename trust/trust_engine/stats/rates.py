"""The three rates, and the partition that makes them meaningful.

Escalation is not an error, so the three metrics have three DIFFERENT denominators:

    all decisions
    |
    +-- acted (agent used its autonomy)      -> denominator for ACCURACY
    |     +-- correct / critical / non-critical
    |
    +-- escalated (agent deferred)           -> NOT counted in accuracy at all
          +-- ruled by a human               -> denominator for HUMAN AGREEMENT
          +-- unruled                        -> excluded entirely

    acted / all                              -> UTILIZATION

Why utilization exists: accuracy-over-acted is P(correct | acted). Maximising it alone
has a degenerate solution — escalate everything, score 100%, do nothing. Utilization is
the coverage term that rules that out.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from shared.contracts import DecisionRecord, ProportionResult

from trust_engine.constants import Z_95
from trust_engine.stats.wilson import wilson_interval


@dataclass(frozen=True, slots=True)
class Partition:
    all_decisions: tuple
    acted: tuple
    escalated: tuple
    ruled_escalations: tuple

    @property
    def n_total(self) -> int:
        return len(self.all_decisions)


def partition(decisions: Sequence[DecisionRecord]) -> Partition:
    ordered = tuple(sorted(decisions, key=lambda d: (d.sequence, d.decision_id)))
    acted = tuple(d for d in ordered if d.is_acted)
    escalated = tuple(d for d in ordered if d.is_escalated)
    ruled = tuple(d for d in escalated if d.has_human_ruling)
    return Partition(ordered, acted, escalated, ruled)


def _proportion(successes: int, trials: int, z: float = Z_95) -> ProportionResult:
    lower, upper = wilson_interval(successes, trials, z)
    return ProportionResult(
        successes=successes,
        trials=trials,
        point=(successes / trials) if trials else None,
        wilson_lower=lower,
        wilson_upper=upper,
    )


def accuracy(decisions: Sequence[DecisionRecord], z: float = Z_95) -> ProportionResult:
    """Correctness over ACTED decisions only. An agent that escalates everything gets
    trials == 0 here, hence a Wilson lower bound of 0.0 and no path to autonomy."""
    p = partition(decisions)
    correct = sum(1 for d in p.acted if d.is_correct)
    return _proportion(correct, len(p.acted), z)


def utilization(decisions: Sequence[DecisionRecord], z: float = Z_95) -> ProportionResult:
    """Fraction of decisions the agent handled itself. Denominator is ALL decisions,
    including escalations — that is the whole point."""
    p = partition(decisions)
    return _proportion(len(p.acted), p.n_total, z)


def human_agreement(decisions: Sequence[DecisionRecord], z: float = Z_95) -> ProportionResult:
    """Agreement between the agent's recommendation and the human's ruling, over
    escalations a human actually ruled on. Unruled escalations are excluded, not
    counted as disagreement — a human who never reviewed tells us nothing."""
    p = partition(decisions)
    agreed = sum(1 for d in p.ruled_escalations if d.human_agreed)
    return _proportion(agreed, len(p.ruled_escalations), z)


@dataclass(frozen=True, slots=True)
class ErrorBreakdown:
    critical: int
    noncritical: int
    acted_total: int

    @property
    def critical_rate(self) -> float:
        return self.critical / self.acted_total if self.acted_total else 0.0

    @property
    def total_errors(self) -> int:
        return self.critical + self.noncritical


def error_breakdown(decisions: Sequence[DecisionRecord]) -> ErrorBreakdown:
    p = partition(decisions)
    return ErrorBreakdown(
        critical=sum(1 for d in p.acted if d.is_critical_error),
        noncritical=sum(1 for d in p.acted if d.is_noncritical_error),
        acted_total=len(p.acted),
    )