"""Response models mirroring the Trust Engine's output contracts.

Every class here mirrors a `shared/contracts.py` frozen dataclass
field-for-field, per docs/lanes/vp.md: "Where a shared frozen dataclass
exists ... mirror it field-for-field rather than inventing a parallel
shape." `backend/tests/test_schema_contracts.py` asserts this holds for
every field, every class, in CI.

The one deliberate addition: `TrustEvaluationOut.id`. `TrustEvaluation`
itself carries no identity field (shared/contracts.py says so explicitly —
"whatever constructs a TrustEvaluation is responsible" for everything a
frozen dataclass can't enforce on itself, and identity is no exception).
The backend mints this id when it persists an evaluation; governance
receives it and echoes it back as `Recommendation.trust_evaluation_ref` —
the trust engine itself never mints or sees an id. See ADR-0011.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict
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
    config_fingerprint: str
