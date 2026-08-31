"""Shared column-type helpers for `backend/app/models/`.

Two concerns:

- **JSONB, with a SQLite fallback.** Production runs on Postgres
  (`docker-compose.yml`), where these columns are real `JSONB` — indexable,
  queryable evidence snapshots (ADR-0013). Tests and the migration-integrity
  check in `backend/tests/test_alembic_migration.py` run against a throwaway
  SQLite file, since no Postgres is available in CI (`.github/workflows/ci.yml`
  installs no database service) or guaranteed on every contributor's machine.
  SQLite has no `JSONB` type; `.with_variant(...)` swaps in a plain `JSON`
  column there. Same data, same access pattern (`.payload["key"]`), a
  dialect-appropriate storage type underneath.
- **Enum columns backed by `shared.enums` values, not member names.** Every
  `str, Enum` in `shared/enums.py` has to serialize as its `.value` (the
  string the whole system already reads and writes), not SQLAlchemy's default
  of the member's `.name`. `AgentState`'s members are especially easy to get
  wrong this way — its values are lowercase (`"probation"`) while its member
  names are uppercase (`PROBATION`), a pre-existing, deliberate asymmetry
  documented in `shared/enums.py`.
"""

from __future__ import annotations

from enum import Enum
from typing import TypeVar

from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import Enum as SAEnum

JSONBType = JSONB().with_variant(JSON(), "sqlite")

_E = TypeVar("_E", bound=Enum)


def enum_column(enum_cls: type[_E], **kwargs) -> SAEnum:
    """A `sqlalchemy.Enum` storing `enum_cls`'s `.value`s as plain strings.

    `native_enum=False` deliberately: a Postgres native `ENUM` type needs
    `ALTER TYPE ... ADD VALUE` (and, before Postgres 12, a transaction-boundary
    workaround) to add a member, which turns "add one value" into a more
    delicate migration than the treaty files in `shared/enums.py` warrant. A
    `VARCHAR` plus a `CHECK` constraint (what `native_enum=False` generates)
    changes with an ordinary migration, and reads identically either way from
    the ORM's side.
    """
    return SAEnum(
        enum_cls,
        values_callable=lambda cls: [member.value for member in cls],
        native_enum=False,
        **kwargs,
    )
