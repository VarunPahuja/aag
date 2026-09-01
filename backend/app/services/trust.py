"""Computing an agent's `TrustEvaluation` from persisted state, and persisting
the result — the one place both `GET /agents/{id}/trust` and
`POST /agents/{id}/recommendations` (which needs fresh evidence to hand
governance) build one, so the two paths can never derive `AgentContext` or
persist a `TrustEvaluation` two different ways.

`trust/` cannot read a clock or mint an id by design (`trust_engine.evaluate`
never touches `datetime.now`) — both are stamped here, at write time, by the
one component actually allowed to hold a clock (docs/lanes/vp.md, ADR-0011).
"""

from __future__ import annotations

import dataclasses
import uuid
from datetime import UTC, datetime
from enum import Enum

from shared.contracts import AgentContext, DecisionRecord, TrustEvaluation
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from trust_engine.evaluate import evaluate

from app.models import Agent, Decision, Invoice, PolicyVersion
from app.models import TrustEvaluation as TrustEvaluationRow
from app.schemas.agent import AgentContextOut


def jsonable(value: object) -> object:
    """Recursively turn a dataclass/Enum/datetime tree into plain JSON-safe
    values, for a JSONB column (`trust_evaluations.payload`,
    `recommendations.agent_opinions`) — the same shapes `dataclasses.asdict()`
    produces, except Enum members serialise as `.value` and datetimes as
    ISO-8601 strings, which plain `asdict()` does not do on its own.
    """
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {f.name: jsonable(getattr(value, f.name)) for f in dataclasses.fields(value)}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    if isinstance(value, dict):
        return {k: jsonable(v) for k, v in value.items()}
    return value


def agent_context(db: Session, agent: Agent) -> AgentContextOut:
    """Real, derived from the tables that exist — `docs/lanes/vp.md`'s
    `agents` schema has no `AgentContext` columns of its own.
    `current_limit`/`state` are the agent row's own fields; the two decision
    counts are computed relative to whichever policy version is currently in
    force: `decisions_since_last_change` is every decision recorded at or
    after that version's `effective_from`; `decisions_since_clawback` is the
    same count, but only when that version was itself a clawback (a lower
    rung than the one before it) — `None` otherwise, meaning "no clawback
    recovery is currently pending."
    """
    versions = (
        db.execute(
            select(PolicyVersion)
            .where(PolicyVersion.agent_id == agent.id)
            .order_by(PolicyVersion.effective_from.desc())
            .limit(2)
        )
        .scalars()
        .all()
    )
    if not versions:
        return AgentContextOut(
            current_limit=agent.current_limit,
            decisions_since_last_change=0,
            decisions_since_clawback=None,
            state=agent.state,
        )

    current = versions[0]
    since_change = (
        db.execute(
            select(func.count())
            .select_from(Decision)
            .where(Decision.agent_id == agent.id, Decision.decided_at >= current.effective_from)
        ).scalar()
        or 0
    )

    is_clawback = len(versions) > 1 and current.rung < versions[1].rung
    since_clawback = since_change if is_clawback else None

    return AgentContextOut(
        current_limit=agent.current_limit,
        decisions_since_last_change=since_change,
        decisions_since_clawback=since_clawback,
        state=agent.state,
    )


def load_decision_records(db: Session, agent_id: str) -> list[DecisionRecord]:
    """The agent's full decision history, ordered by sequence, as the trust
    engine's own input shape. `amount`/`ground_truth` live on `invoices`, not
    `decisions` (same join `app/api/v1/decisions.py`'s `_decision_out` does)."""
    rows = db.execute(
        select(Decision, Invoice)
        .join(Invoice, Decision.invoice_id == Invoice.id)
        .where(Decision.agent_id == agent_id)
        .order_by(Decision.sequence)
    ).all()
    return [
        DecisionRecord(
            decision_id=decision.id,
            sequence=decision.sequence,
            invoice_id=decision.invoice_id,
            amount=invoice.amount,
            action=decision.action,
            ground_truth=invoice.ground_truth_action,
            agent_id=decision.agent_id,
            decided_at=decision.decided_at,
            recommended_action=decision.recommended_action,
            human_ruling=decision.human_ruling,
        )
        for decision, invoice in rows
    ]


def compute_trust_evaluation(db: Session, agent: Agent) -> TrustEvaluation:
    """Evaluate `agent`'s real persisted decision history with the real trust
    engine. Does not persist — see `compute_and_persist_trust_evaluation`.

    On zero decisions, `trust_engine.evaluate` has nothing to read `agent_id`
    from and returns the literal string `"unknown"` (governance/INTEGRATION.md
    flags this explicitly) — corrected here, unconditionally, rather than left
    for every caller to remember.
    """
    decisions = load_decision_records(db, agent.id)
    ctx = agent_context(db, agent)
    context = AgentContext(
        current_limit=ctx.current_limit,
        decisions_since_last_change=ctx.decisions_since_last_change,
        decisions_since_clawback=ctx.decisions_since_clawback,
        state=ctx.state,
    )
    evaluation = evaluate(decisions, context)
    return dataclasses.replace(evaluation, agent_id=agent.id, evaluated_at=datetime.now(UTC))


def persist_trust_evaluation(db: Session, evaluation: TrustEvaluation) -> str:
    """Add a `trust_evaluations` row for `evaluation` to `db` and return the
    minted id. Does not commit — the caller's transaction does.

    Does flush: `app.services.governance.generate_recommendation` references
    this id from a `recommendations` row it adds afterwards, in the same
    session, and Postgres enforces that foreign key — unlike SQLite (no FK
    enforcement by default), which let a real cross-table ordering bug here
    pass every test until it was run live against Postgres. Flushing here,
    at the one place this row is created, means every caller gets a
    genuinely persisted row back, not a hope that some later autoflush
    orders two unrelated `session.add()` calls correctly.
    """
    row_id = f"trust-eval-{evaluation.agent_id}-{uuid.uuid4().hex[:10]}"
    db.add(
        TrustEvaluationRow(
            id=row_id,
            agent_id=evaluation.agent_id,
            evaluated_at=evaluation.evaluated_at,
            trust_score=evaluation.trust_score,
            recommended_limit=evaluation.recommended_limit,
            direction=evaluation.direction,
            payload=jsonable(evaluation),
        )
    )
    db.flush()
    return row_id


def compute_and_persist_trust_evaluation(db: Session, agent: Agent) -> tuple[TrustEvaluation, str]:
    """`compute_trust_evaluation` plus `persist_trust_evaluation`, together —
    what every caller actually wants: a fresh evaluation, on disk, with the
    id that references it."""
    evaluation = compute_trust_evaluation(db, agent)
    row_id = persist_trust_evaluation(db, evaluation)
    return evaluation, row_id
