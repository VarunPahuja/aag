"""The stubbed identity the backend hands every request.

No real JWT yet (docs/lanes/vp.md: "Real JWT later, but the role-check
decorator exists and is applied from the start"). `current_user`
(app/deps.py) reads a header and returns one of these; `require_role`
(app/deps.py) is the role-check mechanism — a FastAPI dependency, which is
this framework's equivalent of a decorator.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class Role(str, Enum):
    """Three roles, one job each.

    ADMIN    — authorizes autonomy increases/decreases (the human sign-off
               ADR-0004 requires) and operates the system (starts simulation
               runs, submits decisions on the ingest path).
    REVIEWER — reviews sampled decisions post-hoc (ADR-0009). Reviewer
               explicitly cannot approve a recommendation — that is ADMIN's
               job alone (docs/lanes/vp.md, Thu 10 Sept security-pass check:
               "Reviewer cannot approve").
    AUDITOR  — read-only everywhere. Watches the audit log and everything
               else; mutates nothing ("auditor is read-only").
    """

    ADMIN = "admin"
    REVIEWER = "reviewer"
    AUDITOR = "auditor"


class CurrentUser(BaseModel):
    """The stubbed principal attached to every request via `Depends(current_user)`."""

    user_id: str
    email: str
    role: Role
