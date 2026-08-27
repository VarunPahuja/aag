"""Simulation-run fixtures — one completed run, one still running.

No `shared/` dataclass to mirror here (see `app/schemas/simulation.py`);
these are built directly as `SimulationRunOut` instances.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.schemas.simulation import RunStatus, SimulationPhase, SimulationRunOut

_NOW = datetime(2026, 8, 27, 12, 0, tzinfo=UTC)

SIMULATION_RUNS: dict[str, SimulationRunOut] = {
    "run-0001": SimulationRunOut(
        run_id="run-0001",
        status=RunStatus.COMPLETED,
        phase=SimulationPhase.GOOD,
        agent_id="agent-01",
        invoice_count=150,
        seed=42,
        started_at=_NOW - timedelta(hours=4),
        completed_at=_NOW - timedelta(hours=3, minutes=50),
        decisions_submitted=150,
        accuracy=0.94,
        wilson_lower_bound=0.887,
    ),
    "run-0002": SimulationRunOut(
        run_id="run-0002",
        status=RunStatus.RUNNING,
        phase=SimulationPhase.DEGRADED,
        agent_id="agent-03",
        invoice_count=200,
        seed=42,
        started_at=_NOW - timedelta(minutes=5),
        completed_at=None,
        decisions_submitted=64,
        accuracy=None,
        wilson_lower_bound=None,
    ),
}
