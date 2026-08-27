"""Append-only policy-version history per agent — `GET /agents/{id}/policy-versions`.

Each row chains to the one it replaced via `previous_version_id`; only the
first row for an agent has `None`. Limits are always real `AUTONOMY_LADDER`
values (`shared.constants.limit_of`), never invented numbers.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from shared.constants import limit_of, rung_of

from app.schemas.agent import PolicyVersionOut

_NOW = datetime(2026, 8, 27, 12, 0, tzinfo=UTC)


def _dt(days_ago: int) -> datetime:
    # Fixture timestamps; real ones come from the DB row's own clock once
    # persistence lands (docs/DEADLINES.md, Fri 28 Aug).
    return _NOW - timedelta(days=days_ago)


POLICY_VERSIONS: dict[str, list[PolicyVersionOut]] = {
    "agent-01": [
        PolicyVersionOut(
            id="pv-agent01-001",
            agent_id="agent-01",
            limit=limit_of(0),
            rung=0,
            effective_from=_dt(30),
            created_by="system",
            reason="Agent onboarded at the autonomy floor.",
            previous_version_id=None,
        ),
        PolicyVersionOut(
            id="pv-agent01-002",
            agent_id="agent-01",
            limit=limit_of(1),
            rung=1,
            effective_from=_dt(20),
            created_by="user-admin-01",
            reason="Evidence cleared all six increase gates; approved rung 0 -> 1.",
            previous_version_id="pv-agent01-001",
        ),
        PolicyVersionOut(
            id="pv-agent01-003",
            agent_id="agent-01",
            limit=limit_of(2),
            rung=2,
            effective_from=_dt(10),
            created_by="user-admin-01",
            reason="Evidence cleared all six increase gates; approved rung 1 -> 2.",
            previous_version_id="pv-agent01-002",
        ),
    ],
    "agent-02": [
        PolicyVersionOut(
            id="pv-agent02-001",
            agent_id="agent-02",
            limit=limit_of(0),
            rung=0,
            effective_from=_dt(5),
            created_by="system",
            reason="Agent onboarded at the autonomy floor.",
            previous_version_id=None,
        ),
    ],
    "agent-03": [
        PolicyVersionOut(
            id="pv-agent03-001",
            agent_id="agent-03",
            limit=limit_of(0),
            rung=0,
            effective_from=_dt(45),
            created_by="system",
            reason="Agent onboarded at the autonomy floor.",
            previous_version_id=None,
        ),
        PolicyVersionOut(
            id="pv-agent03-002",
            agent_id="agent-03",
            limit=limit_of(1),
            rung=1,
            effective_from=_dt(30),
            created_by="user-admin-01",
            reason="Evidence cleared all six increase gates; approved rung 0 -> 1.",
            previous_version_id="pv-agent03-001",
        ),
        PolicyVersionOut(
            id="pv-agent03-003",
            agent_id="agent-03",
            limit=limit_of(2),
            rung=2,
            effective_from=_dt(14),
            created_by="user-admin-01",
            reason="Evidence cleared all six increase gates; approved rung 1 -> 2.",
            previous_version_id="pv-agent03-002",
        ),
        PolicyVersionOut(
            id="pv-agent03-004",
            agent_id="agent-03",
            limit=limit_of(1),
            rung=1,
            effective_from=_dt(2),
            created_by="system",
            reason="Automatic clawback: confirmed drift (CLAWBACK_DRIFT). No human "
            "approval required for a reduction (ADR-0004).",
            previous_version_id="pv-agent03-003",
        ),
    ],
}

assert all(
    rung_of(pv.limit) == pv.rung for versions in POLICY_VERSIONS.values() for pv in versions
), "fixture policy versions must keep limit/rung in sync, same invariant TrustEvaluation documents"
