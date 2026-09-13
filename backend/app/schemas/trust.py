"""Response models mirroring the Trust Engine's output contracts.

Every class here mirrors a `shared/contracts.py` frozen dataclass
field-for-field, per docs/lanes/vp.md: "Where a shared frozen dataclass
exists ... mirror it field-for-field rather than inventing a parallel
shape." `backend/tests/test_schema_contracts.py` asserts this holds for
every field, every class, in CI.

Two deliberate additions: `TrustEvaluationOut.id`. `TrustEvaluation`
itself carries no identity field (shared/contracts.py says so explicitly —
"whatever constructs a TrustEvaluation is responsible" for everything a
frozen dataclass can't enforce on itself, and identity is no exception).
The backend mints this id when it persists an evaluation; governance
receives it and echoes it back as `Recommendation.trust_evaluation_ref` —
the trust engine itself never mints or sees an id. See ADR-0011.

And `TrustEvaluationOut.thresholds` — the gate values the engine applied to
produce this evaluation. Not on the shared dataclass because `shared/` is
frozen, and not derivable by a client: they live in `trust_engine.constants`.
Added because the dashboard was drawing a "safety threshold" at a hardcoded
85% accuracy, a number that exists nowhere in `trust/` or `backend/` — see
`TrustThresholdsOut` below for the full reasoning.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from shared.enums import AgentState, Direction, DriftSeverity


class ProportionResultOut(BaseModel):
    """Mirrors `shared.contracts.ProportionResult` field-for-field."""

    model_config = ConfigDict(from_attributes=True)

    successes: int
    trials: int
    point: float | None
    wilson_lower: float
    wilson_upper: float


class ScoreComponentOut(BaseModel):
    """Mirrors `shared.contracts.ScoreComponent` field-for-field."""

    model_config = ConfigDict(from_attributes=True)

    name: str
    value: float | None
    nominal_weight: float
    effective_weight: float
    available: bool


class DriftResultOut(BaseModel):
    """Mirrors `shared.contracts.DriftResult` field-for-field."""

    model_config = ConfigDict(from_attributes=True)

    severity: DriftSeverity
    detected: bool
    recent_accuracy: float | None
    baseline_accuracy: float | None
    drop_pp: float | None
    z_statistic: float | None
    p_value: float | None
    critical_errors_in_window: int
    recent_n: int
    baseline_n: int
    underpowered: bool


class TrustThresholdsOut(BaseModel):
    """The trust engine's own gate values, sent with the evaluation they
    produced.

    Here because a client that draws a threshold has to get it from somewhere,
    and the only safe somewhere is the engine that applies it.
    `HorizontalThresholdGauge.tsx` used to mark a "safety threshold" at a
    hardcoded 85% accuracy and colour the bar red or green against it — a
    number that appears **nowhere** in `trust/` or `backend/`. The engine has
    no accuracy threshold at all: promotion gates on the *trust score*
    (`MIN_TRUST_SCORE_FOR_INCREASE`), and the accuracy axis is policed by drift
    detection, which compares recent accuracy against the agent's own baseline
    rather than against any fixed line. So the dashboard was not merely
    duplicating a rule in the wrong place; it was displaying one the system
    does not have.

    These are configuration, not per-agent evidence, so they are identical on
    every evaluation. They ride along with it anyway because that is the
    evaluation these exact values produced — a client reading a historical row
    gets the thresholds that applied then, not today's.
    """

    model_config = ConfigDict(from_attributes=True)

    min_sample_for_increase: int
    min_trust_score_for_increase: float
    drift_accuracy_drop_pp: float
    critical_error_window: int
    recent_window: int


def _current_thresholds() -> TrustThresholdsOut:
    """Read from `trust_engine.constants` on every construction, so the API can
    never report a threshold the engine is not actually applying."""
    from trust_engine.constants import (
        CRITICAL_ERROR_WINDOW,
        DRIFT_ACCURACY_DROP_PP,
        MIN_SAMPLE_FOR_INCREASE,
        MIN_TRUST_SCORE_FOR_INCREASE,
        RECENT_WINDOW,
    )

    return TrustThresholdsOut(
        min_sample_for_increase=MIN_SAMPLE_FOR_INCREASE,
        min_trust_score_for_increase=MIN_TRUST_SCORE_FOR_INCREASE,
        drift_accuracy_drop_pp=DRIFT_ACCURACY_DROP_PP,
        critical_error_window=CRITICAL_ERROR_WINDOW,
        recent_window=RECENT_WINDOW,
    )


class TrustEvaluationOut(BaseModel):
    """Mirrors `shared.contracts.TrustEvaluation` field-for-field, plus `id`
    (see module docstring — this is the one backend-minted addition).
    """

    model_config = ConfigDict(from_attributes=True)

    id: str

    agent_id: str
    schema_version: str

    total_decisions: int
    acted_decisions: int
    escalated_decisions: int
    ruled_escalations: int

    accuracy: ProportionResultOut | None
    human_agreement: ProportionResultOut | None
    utilization: ProportionResultOut | None

    critical_errors: int
    noncritical_errors: int
    critical_error_rate: float
    critical_errors_in_recent_window: int

    trust_score: float
    components: list[ScoreComponentOut]
    weights_renormalised: bool

    drift: DriftResultOut

    current_limit: int
    recommended_limit: int
    current_rung: int
    recommended_rung: int
    direction: Direction
    state: AgentState
    eligible_for_increase: bool
    decisions_since_last_change: int

    reason_codes: list[str]
    evaluated_at: datetime | None

    # Defaulted, not required: `TrustEvaluation` (the shared dataclass) has no
    # such field, so every existing construction site keeps working unchanged,
    # and a historical row whose stored payload predates this still validates.
    thresholds: TrustThresholdsOut = Field(default_factory=_current_thresholds)
    config_fingerprint: str
