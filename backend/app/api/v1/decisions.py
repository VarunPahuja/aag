"""Decision resource — the simulator's ingest path, and the read-back of what
was ingested.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, status

from app.api.v1.pagination import PageParam, PageSizeParam, paginate
from app.deps import CurrentUserDep
from app.errors import NOT_FOUND_RESPONSE, not_found
from app.fixtures.decisions import DECISIONS, DECISIONS_BY_ID
from app.schemas.decision import DecisionCreate, DecisionRecordOut
from app.schemas.envelope import Page

router = APIRouter(prefix="/decisions", tags=["decisions"])


@router.post("", response_model=DecisionRecordOut, status_code=status.HTTP_201_CREATED)
def create_decision(body: DecisionCreate, user: CurrentUserDep) -> DecisionRecordOut:
    """Ingest one decision from the simulator (or, eventually, a real agent).

    Once implemented: validates the agent exists and the invoice hasn't
    already been decided, assigns the next `sequence` number for the agent,
    writes a `DecisionRecord`-shaped row, and appends a hash-chained
    `audit_log` entry in the same transaction (docs/lanes/vp.md). This stub
    echoes back a `DecisionRecordOut` built from the request, with a minted
    id and `decided_at`, but does not persist it — call it twice with the
    same body and you get two different ids back.
    """
    return DecisionRecordOut(
        decision_id=f"dec-{uuid.uuid4().hex[:12]}",
        sequence=len(DECISIONS) + 1,
        invoice_id=body.invoice_id,
        amount=body.amount,
        action=body.action,
        ground_truth=body.ground_truth,
        agent_id=body.agent_id,
        decided_at=datetime.now(UTC),
        recommended_action=None,
        human_ruling=None,
    )


@router.get("", response_model=Page[DecisionRecordOut])
def list_decisions(
    user: CurrentUserDep, page: PageParam = 1, page_size: PageSizeParam = 20
) -> Page[DecisionRecordOut]:
    """List decisions, newest first.

    Once implemented: `SELECT ... ORDER BY decided_at DESC`, with
    `?agent_id=` / `?action=` filters — not needed yet, add when the
    dashboard's decisions table asks for them.
    """
    return paginate(list(reversed(DECISIONS)), page, page_size)


@router.get("/{decision_id}", response_model=DecisionRecordOut, responses=NOT_FOUND_RESPONSE)
def get_decision(decision_id: str, user: CurrentUserDep) -> DecisionRecordOut:
    """Fetch one decision by id.

    Once implemented: `SELECT ... WHERE id = :decision_id`, 404 if no row.
    """
    decision = DECISIONS_BY_ID.get(decision_id)
    if decision is None:
        raise not_found(
            "decision_not_found", f"No decision {decision_id!r}.", {"decision_id": decision_id}
        )
    return decision
