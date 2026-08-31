"""The declarative base every ORM model in this package shares.

Nothing beyond that lives here on purpose — `docs/lanes/vp.md` scopes this
package to persistence and audit; enforcement (`backend/app/policy/`) is a
separate module that must never import from here (ADR-0003, ADR-0014).
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
