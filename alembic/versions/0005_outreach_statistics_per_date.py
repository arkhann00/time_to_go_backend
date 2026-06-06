"""Allow multiple outreach statistics per user with outreach_date.

Revision ID: 0005_outreach_statistics_per_date
Revises: 0004_add_outreach_statistics
Create Date: 2026-06-06
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0005_outreach_statistics_per_date"
down_revision = "0004_add_outreach_statistics"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # DROP INDEX IF EXISTS handles both fresh DBs and DBs where the index was created differently.
    op.execute("DROP INDEX IF EXISTS ix_outreach_statistics_user_id")

    # batch_alter_table recreates the table from scratch (required for SQLite DDL changes).
    # Add outreach_date as nullable first; backfill before enforcing NOT NULL.
    with op.batch_alter_table("outreach_statistics", recreate="always") as batch_op:
        batch_op.add_column(sa.Column("outreach_date", sa.Date(), nullable=True))
        batch_op.create_index("ix_outreach_statistics_user_id", ["user_id"], unique=False)

    op.execute("UPDATE outreach_statistics SET outreach_date = '2026-01-01' WHERE outreach_date IS NULL")

    with op.batch_alter_table("outreach_statistics") as batch_op:
        batch_op.alter_column("outreach_date", nullable=False)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_outreach_statistics_user_id")

    with op.batch_alter_table("outreach_statistics", recreate="always") as batch_op:
        batch_op.drop_column("outreach_date")
        batch_op.create_index("ix_outreach_statistics_user_id", ["user_id"], unique=True)
