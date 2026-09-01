"""Add recommendations.governance_mode.

`shared.contracts.Recommendation.governance_mode` / `RecommendationOut`
require it, and no column carried it — found wiring
`POST /agents/{id}/recommendations` (vp/trust-governance-wiring), the same
kind of gap PR #17/#18 found and fixed for `generated_at`.

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-01
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # server_default only at add-time, so any pre-existing row (0001 is
    # already merged and may already be applied elsewhere) lands on "stub"
    # rather than failing NOT NULL; dropped immediately after so every new
    # insert must supply it explicitly, same as every other required column.
    # Batch mode: SQLite (tests, `backend/tests/test_alembic_migration.py`)
    # has no ALTER COLUMN at all — batch mode recreates the table under the
    # hood there and is a plain ALTER on Postgres, same as every other
    # dialect-portable migration in this file.
    with op.batch_alter_table("recommendations") as batch_op:
        batch_op.add_column(
            sa.Column("governance_mode", sa.String(), nullable=False, server_default="stub")
        )
    with op.batch_alter_table("recommendations") as batch_op:
        batch_op.alter_column("governance_mode", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("recommendations") as batch_op:
        batch_op.drop_column("governance_mode")
