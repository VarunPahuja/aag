"""Liveness check. Deliberately unauthenticated — a load balancer or an
uptime probe should not need a role header to ask "are you up."
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel
from shared.constants import SCHEMA_VERSION

router = APIRouter(tags=["health"])


class HealthOut(BaseModel):
    status: str
    schema_version: str


@router.get("/health", response_model=HealthOut)
def health() -> HealthOut:
    """Always 200 while the process is up. No DB check yet — once
    persistence lands, this should also verify a connection round-trip and
    return 503 if the database is unreachable rather than lying about it.
    """
    return HealthOut(status="ok", schema_version=SCHEMA_VERSION)
