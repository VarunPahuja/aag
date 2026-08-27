from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture()
def admin_headers() -> dict[str, str]:
    return {"X-User-Role": "admin"}


@pytest.fixture()
def reviewer_headers() -> dict[str, str]:
    return {"X-User-Role": "reviewer"}


@pytest.fixture()
def auditor_headers() -> dict[str, str]:
    return {"X-User-Role": "auditor"}
