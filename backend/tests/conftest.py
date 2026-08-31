from __future__ import annotations

from pathlib import Path

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from alembic import command
from app.deps import get_session, session_dependency_factory
from app.main import app
from app.seed import seed

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_ALEMBIC_INI = _BACKEND_DIR / "alembic.ini"


@pytest.fixture()
def db_engine(tmp_path, monkeypatch):
    """A freshly migrated, seeded SQLite database, one per test — the same
    pattern `test_seed.py`'s `seeded_session` fixture uses, exposed here so
    any test file can get a real database: either through `client` below, or
    directly (`Session(db_engine)`) for assertions the HTTP layer can't make
    on its own, like inspecting `Decision.within_limit`, the
    `policy_version_id` a decision actually referenced, or the audit log.
    """
    db_path = tmp_path / "api_test.db"
    url = f"sqlite:///{db_path}"
    monkeypatch.setenv("DATABASE_URL", url)
    command.upgrade(Config(str(_ALEMBIC_INI)), "head")

    engine = create_engine(url)
    with Session(engine) as session:
        seed(session)

    yield engine
    engine.dispose()


@pytest.fixture()
def client(db_engine) -> TestClient:
    """Every route wired to the database (decisions, agents) talks to
    `db_engine` above through `app.dependency_overrides` — the same
    commit-on-success/rollback-on-exception dependency the real app uses
    (`session_dependency_factory`, `app/deps.py`), just pointed at the test
    database instead of `DATABASE_URL`.
    """
    session_maker = sessionmaker(bind=db_engine)
    app.dependency_overrides[get_session] = session_dependency_factory(session_maker)
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest.fixture()
def admin_headers() -> dict[str, str]:
    return {"X-User-Role": "admin"}


@pytest.fixture()
def reviewer_headers() -> dict[str, str]:
    return {"X-User-Role": "reviewer"}


@pytest.fixture()
def auditor_headers() -> dict[str, str]:
    return {"X-User-Role": "auditor"}
