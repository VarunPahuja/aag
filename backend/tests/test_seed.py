"""`app/seed.py`: three agents telling one coherent story, deterministic —
same output every run, and consistent with `app/fixtures/` (no contradicting
ids, states, or narrative between the fixture-stubbed API and the seeded DB).
"""

from __future__ import annotations

import itertools
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from alembic import command
from app.models import (
    Agent,
    Approval,
    AuditLogEntry,
    AuditSample,
    Decision,
    Invoice,
    PolicyVersion,
    Recommendation,
)
from app.models import TrustEvaluation as TrustEvaluationRow
from app.models.audit_hash import GENESIS_HASH, compute_hash
from app.seed import seed

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_ALEMBIC_INI = _BACKEND_DIR / "alembic.ini"


@pytest.fixture()
def seeded_session(tmp_path, monkeypatch):
    db_path = tmp_path / "seed_test.db"
    url = f"sqlite:///{db_path}"
    monkeypatch.setenv("DATABASE_URL", url)
    command.upgrade(Config(str(_ALEMBIC_INI)), "head")

    engine = create_engine(url)
    with Session(engine) as session:
        seed(session)
        yield session
    engine.dispose()


def _count(session: Session, model) -> int:
    return session.execute(select(func.count()).select_from(model)).scalar_one()


def test_seeds_three_agents_with_the_documented_story(seeded_session):
    agents = {a.id: a for a in seeded_session.query(Agent).all()}
    assert set(agents) == {"agent-01", "agent-02", "agent-03"}

    assert agents["agent-01"].current_limit == 2500
    assert agents["agent-01"].current_rung == 2
    assert agents["agent-01"].state.value == "active"

    assert agents["agent-02"].current_limit == 500
    assert agents["agent-02"].current_rung == 0
    assert agents["agent-02"].state.value == "probation"

    assert agents["agent-03"].current_limit == 1000
    assert agents["agent-03"].current_rung == 1
    assert agents["agent-03"].state.value == "restricted"


def test_every_table_has_at_least_one_row(seeded_session):
    for model in (
        Agent,
        Invoice,
        Decision,
        PolicyVersion,
        TrustEvaluationRow,
        Recommendation,
        Approval,
        AuditSample,
        AuditLogEntry,
    ):
        assert _count(seeded_session, model) > 0, f"{model.__name__} has no seed rows"


def test_agent03_clawback_chain_is_intact(seeded_session):
    versions = (
        seeded_session.query(PolicyVersion)
        .filter(PolicyVersion.agent_id == "agent-03")
        .order_by(PolicyVersion.effective_from)
        .all()
    )
    ids = [v.id for v in versions]
    assert ids == ["pv-agent03-001", "pv-agent03-002", "pv-agent03-003", "pv-agent03-004"]
    # Each chains to the one before it; the first chains to nothing.
    assert versions[0].previous_version_id is None
    for earlier, later in itertools.pairwise(versions):
        assert later.previous_version_id == earlier.id
    assert (versions[-1].limit, versions[-1].rung) == (1000, 1)


def test_the_critical_error_decision_references_the_pre_clawback_policy_version(seeded_session):
    # dec-agent03-0193 is the APPROVE-when-ground-truth-is-REJECT decision
    # that triggers the clawback — it must reference the version in force
    # *before* the clawback (rung 2), not after.
    decision = seeded_session.get(Decision, "dec-agent03-0193")
    assert decision.policy_version_id == "pv-agent03-003"

    invoice = seeded_session.get(Invoice, decision.invoice_id)
    assert invoice.ground_truth_action.value == "REJECT"
    assert decision.action.value == "APPROVE"


def test_recovery_decisions_reference_the_post_clawback_policy_version(seeded_session):
    for decision_id in ("dec-agent03-0194", "dec-agent03-0195"):
        decision = seeded_session.get(Decision, decision_id)
        assert decision.policy_version_id == "pv-agent03-004"


def test_within_limit_is_computed_by_the_real_policy_engine_not_hardcoded(seeded_session):
    # dec-agent01-0149 (amount 2400, limit 2500 at the time) is within limit
    # even though the agent chose to escalate — within_limit is a fact about
    # the amount vs. the ceiling, independent of the action taken.
    decision = seeded_session.get(Decision, "dec-agent01-0149")
    assert decision.within_limit is True
    assert decision.action.value == "ESCALATE"


def test_audit_log_hash_chain_is_valid(seeded_session):
    entries = seeded_session.query(AuditLogEntry).order_by(AuditLogEntry.ts).all()
    assert len(entries) >= 1
    prev_hash = GENESIS_HASH
    for entry in entries:
        assert entry.prev_hash == prev_hash
        assert entry.hash == compute_hash(prev_hash, entry.payload)
        prev_hash = entry.hash


def test_agents_current_limit_matches_its_latest_policy_version(seeded_session):
    for agent_id in ("agent-01", "agent-02", "agent-03"):
        agent = seeded_session.get(Agent, agent_id)
        latest = (
            seeded_session.query(PolicyVersion)
            .filter(PolicyVersion.agent_id == agent_id)
            .order_by(PolicyVersion.effective_from.desc())
            .first()
        )
        assert agent.current_limit == latest.limit
        assert agent.current_rung == latest.rung


def test_seed_is_deterministic_across_two_fresh_databases(tmp_path, monkeypatch):
    def _seed_and_dump(db_path):
        url = f"sqlite:///{db_path}"
        monkeypatch.setenv("DATABASE_URL", url)
        command.upgrade(Config(str(_ALEMBIC_INI)), "head")
        engine = create_engine(url)
        with Session(engine) as session:
            seed(session)
            agents = [
                (a.id, a.current_limit, a.current_rung, a.state.value)
                for a in session.query(Agent).order_by(Agent.id)
            ]
            decisions = [
                (d.id, d.within_limit, d.policy_version_id)
                for d in session.query(Decision).order_by(Decision.id)
            ]
            hashes = [e.hash for e in session.query(AuditLogEntry).order_by(AuditLogEntry.ts)]
        engine.dispose()
        return agents, decisions, hashes

    first = _seed_and_dump(tmp_path / "a.db")
    second = _seed_and_dump(tmp_path / "b.db")
    assert first == second
