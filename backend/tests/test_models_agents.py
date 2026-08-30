"""`Agent`'s `rung_of(current_limit) == current_rung` invariant
(`shared.contracts.TrustEvaluation`'s own docstring; `app/models/agents.py`'s
`ck_agents_rung_matches_limit`)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from shared.constants import AUTONOMY_LADDER
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Agent, Base

_NOW = datetime(2026, 8, 27, 12, 0, tzinfo=UTC)


@pytest.fixture()
def engine():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


@pytest.mark.parametrize("rung,limit", list(enumerate(AUTONOMY_LADDER)))
def test_every_real_ladder_pair_is_accepted(engine, rung, limit):
    with Session(engine) as session:
        session.add(
            Agent(
                id=f"agent-rung-{rung}",
                name="x",
                current_limit=limit,
                current_rung=rung,
                state="active",
                created_at=_NOW,
            )
        )
        session.commit()  # must not raise


def test_mismatched_limit_and_rung_is_rejected(engine):
    with Session(engine) as session:
        session.add(
            Agent(
                id="agent-01",
                name="x",
                current_limit=500,
                current_rung=2,
                state="active",
                created_at=_NOW,
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()


def test_limit_not_on_the_ladder_at_all_is_rejected(engine):
    with Session(engine) as session:
        session.add(
            Agent(
                id="agent-01",
                name="x",
                current_limit=750,
                current_rung=0,
                state="active",
                created_at=_NOW,
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
