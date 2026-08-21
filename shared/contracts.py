"""The contracts between the four lanes. TREATY FILE — all four reviewers.

Plain dataclasses, no Pydantic, no ORM, no framework. The Trust Engine must stay
importable with nothing but the standard library plus NumPy/SciPy.

`DecisionRecord` is the simulator's output and the Trust Engine's input.
`TrustEvaluation` is the Trust Engine's output and the backend's input.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from shared.constants import AUTONOMY_FLOOR, SCHEMA_VERSION
from shared.enums import (
    Action,
    AgentState,
    Direction,
    DriftSeverity,
    OpinionVerdict,
    RecommendationStatus,
    ReviewVerdict,
)


# --- simulator -> trust engine -------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DecisionRecord:
    """One decision by the governed agent, with its ground truth known."""

    decision_id: str
    sequence: int
    invoice_id: str
    amount: int
    action: Action
    ground_truth: Action
    agent_id: str = "agent-01"
    decided_at: datetime | None = None

    recommended_action: Action | None = None
    human_ruling: Action | None = None

    @property
    def is_escalated(self) -> bool:
        return self.action is Action.ESCALATE

    @property
    def is_acted(self) -> bool:
        return not self.is_escalated

    @property
    def is_correct(self) -> bool | None:
        if self.is_escalated:
            return None
        return self.action is self.ground_truth

    @property
    def is_critical_error(self) -> bool:
        return self.action is Action.APPROVE and self.ground_truth is Action.REJECT

    @property
    def is_noncritical_error(self) -> bool:
        return self.action is Action.REJECT and self.ground_truth is Action.APPROVE

    @property
    def has_human_ruling(self) -> bool:
        return (
            self.is_escalated
            and self.human_ruling is not None
            and self.recommended_action is not None
        )

    @property
    def human_agreed(self) -> bool | None:
        if not self.has_human_ruling:
            return None
        return self.recommended_action is self.human_ruling


# --- trust engine -> backend ---------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ProportionResult:
    """A count with its confidence bound attached."""

    successes: int
    trials: int
    point: float | None
    wilson_lower: float
    wilson_upper: float

    @property
    def has_evidence(self) -> bool:
        return self.trials > 0


@dataclass(frozen=True, slots=True)
class ScoreComponent:
    name: str
    value: float | None
    nominal_weight: float
    effective_weight: float
    available: bool

    @property
    def contribution(self) -> float:
        return (self.value or 0.0) * self.effective_weight


@dataclass(frozen=True, slots=True)
class AgentContext:
    """The agent's current standing, supplied by the backend."""

    current_limit: int = AUTONOMY_FLOOR
    decisions_since_last_change: int = 0
    decisions_since_clawback: int | None = None
    state: AgentState = AgentState.PROBATION


@dataclass(frozen=True, slots=True)
class DriftResult:
    severity: DriftSeverity = DriftSeverity.NONE
    detected: bool = False
    recent_accuracy: float | None = None
    baseline_accuracy: float | None = None
    drop_pp: float | None = None
    z_statistic: float | None = None
    p_value: float | None = None
    critical_errors_in_window: int = 0
    recent_n: int = 0
    baseline_n: int = 0
    underpowered: bool = False


@dataclass(frozen=True, slots=True)
class TrustEvaluation:
    """The Trust Engine's complete output. Pure evidence plus a recommendation.

    Invariant — `eligible_for_increase` vs. `direction`: `direction == Direction.INCREASE`
    implies `eligible_for_increase` is `True`, but the reverse does not hold.
    `eligible_for_increase == True` together with `direction == Direction.HOLD` is a
    legal, meaningful state — the evidence supports an increase, but a cooldown or a
    post-clawback recovery period is blocking it from being applied right now. That
    state is accompanied by `COOLDOWN_ACTIVE` or `CLAWBACK_RECOVERY_PENDING` in
    `reason_codes` (shared/reason_codes.py) — read `reason_codes`, not `direction`
    alone, to tell "not eligible" apart from "eligible but blocked."

    Invariant — `current_limit` vs. `current_rung`: `rung_of(current_limit) ==
    current_rung` (shared/constants.py) must always hold, and the same applies to
    `recommended_limit` / `recommended_rung`. This dataclass is frozen and cannot
    enforce that itself — whatever constructs a TrustEvaluation is responsible for
    keeping each pair in sync.
    """

    agent_id: str
    schema_version: str = SCHEMA_VERSION

    total_decisions: int = 0
    acted_decisions: int = 0
    escalated_decisions: int = 0
    ruled_escalations: int = 0

    accuracy: ProportionResult | None = None
    human_agreement: ProportionResult | None = None
    utilization: ProportionResult | None = None

    critical_errors: int = 0
    noncritical_errors: int = 0
    critical_error_rate: float = 0.0
    critical_errors_in_recent_window: int = 0

    trust_score: float = 0.0
    components: tuple[ScoreComponent, ...] = ()
    weights_renormalised: bool = False

    drift: DriftResult = field(default_factory=DriftResult)

    current_limit: int = 0
    recommended_limit: int = 0
    current_rung: int = 0
    recommended_rung: int = 0
    direction: Direction = Direction.HOLD
    state: AgentState = AgentState.PROBATION
    eligible_for_increase: bool = False
    decisions_since_last_change: int = 0

    reason_codes: tuple[str, ...] = ()
    evaluated_at: datetime | None = None
    config_fingerprint: str = ""


# --- governance -> backend -------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AgentOpinion:
    """One governance agent's stance on a recommendation, before opinions are combined
    into a single Recommendation. `agent_name` is one of: risk, performance,
    compliance, audit.
    """

    agent_name: str
    verdict: OpinionVerdict
    reasoning: str
    concerns: tuple[str, ...] = ()
    confidence: float = 0.0


@dataclass(frozen=True, slots=True)
class Recommendation:
    """Governance's complete output: a proposed autonomy change plus the panel of
    opinions and reasoning behind it. Mirrors TrustEvaluation's role for the trust
    lane — this is what vc/governance emits and the backend consumes.

    `trust_evaluation_ref` links back to the TrustEvaluation this recommendation was
    computed from — governance reasons about evidence, it does not originate it (see
    ADR-0001). `proposed_limit` / `proposed_rung` are what governance is asking for;
    they are not applied until a human authorizes them (ADR-0004), and the backend may
    reduce `proposed_limit` against a hard ceiling before authorization is even
    possible — `clamped` and `clamped_from` record when that happened and what the
    original ask was.
    """

    recommendation_id: str
    agent_id: str
    schema_version: str = SCHEMA_VERSION

    direction: Direction = Direction.HOLD
    proposed_limit: int = AUTONOMY_FLOOR
    proposed_rung: int = 0
    rationale: str = ""

    opinions: tuple[AgentOpinion, ...] = ()
    has_dissent: bool = False
    confidence: float = 0.0

    governance_mode: str = "stub"
    status: RecommendationStatus = RecommendationStatus.PENDING
    trust_evaluation_ref: str | None = None
    generated_at: datetime | None = None

    clamped: bool = False
    clamped_from: int | None = None


# --- human review -> trust engine (ground truth beyond the simulator) -------------------


@dataclass(frozen=True, slots=True)
class AuditSample:
    """A decision pulled for human review under the rung-scaled sampling rate (see
    shared/constants.py:SAMPLING_RATE_BY_RUNG). Once the system runs past the
    simulator, where DecisionRecord.ground_truth no longer exists, reviewed samples
    are the ground-truth source that ground_truth used to be.
    """

    sample_id: str
    decision_id: str
    agent_id: str
    sampled_at: datetime | None = None
    reviewed_at: datetime | None = None
    reviewer: str | None = None
    verdict: ReviewVerdict | None = None
    reviewer_action: Action | None = None

    @property
    def is_reviewed(self) -> bool:
        return self.reviewed_at is not None and self.verdict is not None

    @property
    def is_pending(self) -> bool:
        return not self.is_reviewed