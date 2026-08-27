"""Simulation-run resource — start a batch, check its status."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, status

from app.deps import CurrentUserDep, require_role
from app.errors import FORBIDDEN_RESPONSE, NOT_FOUND_RESPONSE, not_found
from app.fixtures.simulation import SIMULATION_RUNS
from app.schemas.simulation import RunStatus, SimulationRunCreate, SimulationRunOut
from app.schemas.user import Role

router = APIRouter(prefix="/simulation", tags=["simulation"])

# Starting a run is an operational action, not a governance authorization, but
# it still changes state, so it's still gated (ADMIN operates the system).
_admin_only = Depends(require_role(Role.ADMIN))


@router.post(
    "/runs",
    response_model=SimulationRunOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_admin_only],
    responses=FORBIDDEN_RESPONSE,
)
def start_simulation_run(body: SimulationRunCreate) -> SimulationRunOut:
    """Start a simulation run — the simulator generates `invoice_count`
    synthetic invoices for `phase` and posts each resulting decision to
    `POST /api/v1/decisions`.

    Once implemented: enqueues the run (no Celery — see docs/CONTEXT.md's
    cut-scope list; a background task or a synchronous call is enough for
    this project's scale) and returns immediately with `status=pending`.
    This stub returns a freshly-minted run in `pending` status without
    actually starting anything.
    """
    return SimulationRunOut(
        run_id=f"run-{uuid.uuid4().hex[:8]}",
        status=RunStatus.PENDING,
        phase=body.phase,
        agent_id=body.agent_id,
        invoice_count=body.invoice_count,
        seed=body.seed,
        started_at=datetime.now(UTC),
        completed_at=None,
        decisions_submitted=0,
        accuracy=None,
        wilson_lower_bound=None,
    )


@router.get("/runs/{run_id}", response_model=SimulationRunOut, responses=NOT_FOUND_RESPONSE)
def get_simulation_run(run_id: str, user: CurrentUserDep) -> SimulationRunOut:
    """Poll a run's status and, once complete, its summary accuracy/Wilson
    lower bound over the decisions it submitted.

    Once implemented: `SELECT ... WHERE id = :run_id`, 404 if no row.
    """
    run = SIMULATION_RUNS.get(run_id)
    if run is None:
        raise not_found("simulation_run_not_found", f"No simulation run {run_id!r}.", {"run_id": run_id})
    return run
