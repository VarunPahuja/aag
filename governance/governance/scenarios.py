"""The five situations the demo has to be able to show, as raw decision histories.

Each scenario defines **decisions and context only** — no statistics. Every number the
agents see is produced by `trust_engine.evaluate()`, exactly as it would be in
production. Hand-building a `TrustEvaluation` here would mean recording model responses
to evidence the trust engine would never actually emit, and the first time the two
disagreed would be in front of a panel.

**This module imports the trust lane, and it is the only thing in `governance/` that
does.** That is a deliberate, narrow exception: it exists to *generate fixtures* for the
recording script, runs at development time, and is never on the path a backend request
takes. Cached replay does not import it — the backend supplies its own `TrustEvaluation`
and the cache key is computed from that. If this import ever becomes load-bearing at
request time, something has gone wrong with the layering.

The five were chosen because each one makes a different agent the interesting one:

- `healthy_increase`   — everything agrees. The boring case, and the demo needs one.
- `thin_sample`        — 10/10, bound 72.2%. Performance objects. **The headline case.**
- `active_drift`       — measured degradation. Performance objects on different grounds.
- `critical_error`     — money went out the door. Risk objects.
- `at_ceiling`         — top rung. Compliance has something to say and the others abstain.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from shared.contracts import AgentContext, DecisionRecord, TrustEvaluation
from shared.enums import Action, AgentState

BASE_TIME = datetime(2026, 7, 1, tzinfo=UTC)
AGENT_ID = "agent-demo-01"


def _decision(
    index: int,
    action: Action,
    ground_truth: Action,
    *,
    amount: int = 500,
) -> DecisionRecord:
    return DecisionRecord(
        decision_id=f"dec_{index:06d}",
        sequence=index,
        invoice_id=f"inv_{index:06d}",
        amount=amount,
        action=action,
        ground_truth=ground_truth,
        recommended_action=None,
        human_ruling=None,
        decided_at=BASE_TIME + timedelta(minutes=index),
        agent_id=AGENT_ID,
    )


def _correct(index: int, **kw: object) -> DecisionRecord:
    return _decision(index, Action.APPROVE, Action.APPROVE, **kw)  # type: ignore[arg-type]


def _critical(index: int, **kw: object) -> DecisionRecord:
    """Approved something that should have been rejected. Money left the company."""
    return _decision(index, Action.APPROVE, Action.REJECT, **kw)  # type: ignore[arg-type]


def _noncritical(index: int, **kw: object) -> DecisionRecord:
    """Rejected a valid invoice. Recoverable — someone re-submits."""
    return _decision(index, Action.REJECT, Action.APPROVE, **kw)  # type: ignore[arg-type]


@dataclass(frozen=True, slots=True)
class Scenario:
    """One named situation, and how to turn it into evidence."""

    name: str
    description: str
    decisions: Callable[[], Sequence[DecisionRecord]]
    context: AgentContext

    def build(self) -> TrustEvaluation:
        """Run the real trust engine over this scenario's history.

        Imported inside the method rather than at module scope so that importing
        `governance` never requires the trust package to be installed. Only the
        recording script reaches this code path.
        """
        from trust_engine.evaluate import evaluate

        return evaluate(list(self.decisions()), self.context)


def _healthy() -> list[DecisionRecord]:
    """196/200 correct, four non-critical errors. Wilson lower bound around 95%."""
    decisions = [_correct(i) for i in range(196)]
    decisions += [_noncritical(196 + i) for i in range(4)]
    return decisions


def _thin() -> list[DecisionRecord]:
    """Ten for ten. Point estimate 100%, Wilson lower bound 72.2%."""
    return [_correct(i) for i in range(10)]


def _drifting() -> list[DecisionRecord]:
    """Strong baseline, then a recent block of errors. The drift test should fire."""
    decisions = [_correct(i) for i in range(120)]
    decisions += [_noncritical(120 + i) for i in range(18)]
    decisions += [_correct(138 + i) for i in range(2)]
    return decisions


def _critical_error() -> list[DecisionRecord]:
    """Long clean run with two critical errors late. Non-critical count stays low."""
    decisions = [_correct(i) for i in range(140)]
    decisions += [_critical(140), _critical(141)]
    decisions += [_correct(142 + i) for i in range(8)]
    return decisions


def _contested_increase() -> list[DecisionRecord]:
    """Mediocre but not failing, over a sample large enough to clear every gate.

    The point of this scenario is the *width* of the interval, not its position. Errors
    are spread evenly rather than clustered so the drift test stays silent — the only
    thing wrong with this record is that it is imprecise, and imprecision is exactly
    what a threshold check cannot see and a reasoning panel can.
    """
    decisions: list[DecisionRecord] = []
    for index in range(110):
        # Every sixth decision is a non-critical error. Even spacing keeps the recent
        # window and the baseline at the same rate, so `drift.detected` stays False and
        # the increase is not blocked before an agent gets to argue about it.
        if index % 6 == 5:
            decisions.append(_noncritical(index))
        else:
            decisions.append(_correct(index))
    return decisions


def _at_ceiling() -> list[DecisionRecord]:
    """Excellent record on an agent already at the top rung — nowhere left to go."""
    decisions = [_correct(i, amount=9500) for i in range(240)]
    decisions += [_noncritical(240 + i, amount=9500) for i in range(3)]
    return decisions


SCENARIOS: tuple[Scenario, ...] = (
    Scenario(
        name="healthy_increase",
        description="196/200, bound ~95%. All four agents should concur.",
        decisions=_healthy,
        context=AgentContext(
            current_limit=1000,
            decisions_since_last_change=200,
            decisions_since_clawback=None,
            state=AgentState.ACTIVE,
        ),
    ),
    Scenario(
        name="thin_sample",
        description=(
            "10/10 = 100%, Wilson lower bound 72.2%. The engine already holds, so an "
            "objection could not change the outcome — recorded, the panel concurs and "
            "abstains. Contrast with contested_increase."
        ),
        decisions=_thin,
        context=AgentContext(
            current_limit=500,
            decisions_since_last_change=10,
            decisions_since_clawback=None,
            state=AgentState.PROBATION,
        ),
    ),
    Scenario(
        name="active_drift",
        description="Recent accuracy well below baseline. Measured degradation, not noise.",
        decisions=_drifting,
        context=AgentContext(
            current_limit=2500,
            decisions_since_last_change=140,
            decisions_since_clawback=None,
            state=AgentState.ACTIVE,
        ),
    ),
    Scenario(
        name="critical_error",
        description="Two approvals that should have been rejections. Risk should object.",
        decisions=_critical_error,
        context=AgentContext(
            current_limit=2500,
            decisions_since_last_change=150,
            decisions_since_clawback=None,
            state=AgentState.ACTIVE,
        ),
    ),
    Scenario(
        name="contested_increase",
        description=(
            "~85% over 110, a wide interval on a proposed increase. The one scenario "
            "where dissent can actually bite: every other INCREASE here is unanimous."
        ),
        decisions=_contested_increase,
        context=AgentContext(
            current_limit=1000,
            # At or above COOLDOWN_BETWEEN_INCREASES, and consistent with the history
            # length — an agent that has never had its limit changed has been at this
            # rung for its whole record. Inventing a larger number to clear the cooldown
            # would render evidence that contradicts itself.
            decisions_since_last_change=110,
            decisions_since_clawback=None,
            state=AgentState.ACTIVE,
        ),
    ),
    Scenario(
        name="at_ceiling",
        description="Strong record at the top rung. No increase is available to propose.",
        decisions=_at_ceiling,
        context=AgentContext(
            current_limit=10000,
            decisions_since_last_change=243,
            decisions_since_clawback=None,
            state=AgentState.ACTIVE,
        ),
    ),
)

SCENARIOS_BY_NAME = {scenario.name: scenario for scenario in SCENARIOS}
