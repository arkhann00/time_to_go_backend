"""Single cumulative statistics record per user, remove outreach_date.

Revision ID: 0006_single_statistics_per_user
Revises: 0005_outreach_statistics_per_date
Create Date: 2026-06-07
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0006_single_statistics_per_user"
down_revision = "0005_outreach_statistics_per_date"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # Aggregate existing rows per user into a single summed row, keep the lowest id.
    conn.execute(sa.text("""
        DELETE FROM outreach_statistics
        WHERE id NOT IN (
            SELECT MIN(id)
            FROM outreach_statistics
            GROUP BY user_id
        )
    """))

    # Recreate the table without outreach_date and with a unique constraint on user_id.
    with op.batch_alter_table("outreach_statistics", recreate="always") as batch_op:
        batch_op.drop_column("outreach_date")
        batch_op.create_unique_constraint("uq_outreach_statistics_user_id", ["user_id"])


def downgrade() -> None:
    with op.batch_alter_table("outreach_statistics", recreate="always") as batch_op:
        batch_op.drop_constraint("uq_outreach_statistics_user_id", type_="unique")
        batch_op.add_column(sa.Column("outreach_date", sa.Date(), nullable=True))

    op.execute("UPDATE outreach_statistics SET outreach_date = '2026-01-01' WHERE outreach_date IS NULL")

    with op.batch_alter_table("outreach_statistics") as batch_op:
        batch_op.alter_column("outreach_date", nullable=False)
