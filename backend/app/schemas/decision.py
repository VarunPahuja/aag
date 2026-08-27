"""Decision response and ingest-request models.

`DecisionRecordOut` mirrors `shared.contracts.DecisionRecord` field-for-field
(including `ground_truth` — present on the dataclass because "every synthetic
invoice carries a deterministic correct answer" while the simulator is the
only decision source; once real invoices arrive this field's meaning changes,
not its shape — see `shared/contracts.py` and ADR-0009).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from shared.enums import Action


class DecisionRecordOut(BaseModel):
    """Mirrors `shared.contracts.DecisionRecord` field-for-field."""

    model_config = ConfigDict(from_attributes=True)

    decision_id: str
    sequence: int
    invoice_id: str
    amount: int
    action: Action
    ground_truth: Action
    agent_id: str
    decided_at: datetime | None
    recommended_action: Action | None
    human_ruling: Action | None


class DecisionCreate(BaseModel):
    """Request body for `POST /api/v1/decisions` — the simulator's ingest path.

    Every field needed to construct a `DecisionRecord` (see
    `shared.contracts.DecisionRecord`), plus `reason`
    (cross-cutting rule: every state-changing endpoint requires one — here,
    why this decision is being submitted, e.g. which simulation run or
    invoice-processing batch produced it).
    """

    invoice_id: str
    amount: int = Field(gt=0)
    action: Action
    ground_truth: Action
    agent_id: str
    reason: str = Field(min_length=1, description="Why this decision is being submitted")
