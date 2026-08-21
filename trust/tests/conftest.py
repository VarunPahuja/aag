"""Deterministic fixture builders. No randomness anywhere — a failing statistical test
that can't be reproduced exactly is worse than no test at all.
"""

from __future__ import annotations

import itertools
from datetime import datetime, timedelta, timezone

import pytest

from shared.contracts import DecisionRecord
from shared.enums import Action

_seq = itertools.count()
BASE = datetime(2026, 7, 1, tzinfo=timezone.utc)


def decision(
    action: Action,
    ground_truth: Action,
    *,
    recommended_action: Action | None = None,
    human_ruling: Action | None = None,
    amount: int = 500,
    sequence: int | None = None,
) -> DecisionRecord:
    n = sequence if sequence is not None else next(_seq)
    return DecisionRecord(
        decision_id=f"dec_{n:06d}",
        sequence=n,
        invoice_id=f"inv_{n:06d}",
        amount=amount,
        action=action,
        ground_truth=ground_truth,
        recommended_action=recommended_action,
        human_ruling=human_ruling,
        decided_at=BASE + timedelta(minutes=n),
    )


def correct_approval(**kw) -> DecisionRecord:
    return decision(Action.APPROVE, Action.APPROVE, **kw)


def correct_rejection(**kw) -> DecisionRecord:
    return decision(Action.REJECT, Action.REJECT, **kw)


def critical_error(**kw) -> DecisionRecord:
    """Approved something that should have been rejected."""
    return decision(Action.APPROVE, Action.REJECT, **kw)


def noncritical_error(**kw) -> DecisionRecord:
    """Rejected a valid invoice."""
    return decision(Action.REJECT, Action.APPROVE, **kw)


def escalation(
    *,
    recommended: Action | None = Action.APPROVE,
    ruling: Action | None = Action.APPROVE,
    ground_truth: Action = Action.APPROVE,
    **kw,
) -> DecisionRecord:
    return decision(
        Action.ESCALATE,
        ground_truth,
        recommended_action=recommended,
        human_ruling=ruling,
        **kw,
    )


def run(n: int, factory, **kw) -> list[DecisionRecord]:
    return [factory(**kw) for _ in range(n)]