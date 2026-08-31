"""Verifies the one Alembic migration (`backend/alembic/versions/0001_initial_schema.py`)
applies cleanly to an empty database and that downgrading returns it to empty.

Runs against a throwaway SQLite file, not Postgres — no database service runs
in CI (`.github/workflows/ci.yml`) or is guaranteed on every contributor's
machine (`docker-compose.yml` needs Docker, which isn't always installed).
SQLite exercises the same migration code path (`env.py` reads `DATABASE_URL`
exactly the same way); the one thing it can't verify is Postgres-specific
behavior, which is why `app/models/types.py`'s JSONB columns are written with
an explicit `.with_variant(sa.JSON(), "sqlite")` fallback rather than assuming
one dialect.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from alembic import command

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_ALEMBIC_INI = _BACKEND_DIR / "alembic.ini"

_EXPECTED_TABLES = {
    "agents",
    "approvals",
    "audit_log",
    "audit_samples",
    "decisions",
    "invoices",
    "policy_versions",
    "recommendations",
    "trust_evaluations",
    "users",
}


@pytest.fixture()
def sqlite_url(tmp_path, monkeypatch) -> str:
    db_path = tmp_path / "migration_test.db"
    url = f"sqlite:///{db_path}"
    monkeypatch.setenv("DATABASE_URL", url)
    return url


@pytest.fixture()
def alembic_config() -> Config:
    return Config(str(_ALEMBIC_INI))


def _table_names(url: str) -> set[str]:
    engine = create_engine(url)
    try:
        return set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def test_upgrade_head_creates_every_table(sqlite_url, alembic_config):
    command.upgrade(alembic_config, "head")
    tables = _table_names(sqlite_url)
    assert _EXPECTED_TABLES <= tables


def test_downgrade_base_returns_to_empty(sqlite_url, alembic_config):
    command.upgrade(alembic_config, "head")
    command.downgrade(alembic_config, "base")
    tables = _table_names(sqlite_url) - {"alembic_version"}
    assert tables == set()


def test_upgrade_is_idempotent_up_then_down_then_up_again(sqlite_url, alembic_config):
    command.upgrade(alembic_config, "head")
    command.downgrade(alembic_config, "base")
    command.upgrade(alembic_config, "head")
    tables = _table_names(sqlite_url)
    assert _EXPECTED_TABLES <= tables
