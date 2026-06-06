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
    op.drop_index("ix_outreach_statistics_user_id", table_name="outreach_statistics")

    op.add_column(
        "outreach_statistics",
        sa.Column(
            "outreach_date",
            sa.Date(),
            nullable=False,
            server_default=sa.text("(date('now'))"),
        ),
    )

    op.create_index(
        "ix_outreach_statistics_user_id",
        "outreach_statistics",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_outreach_statistics_user_id", table_name="outreach_statistics")
    op.drop_column("outreach_statistics", "outreach_date")
    op.create_index(
        "ix_outreach_statistics_user_id",
        "outreach_statistics",
        ["user_id"],
        unique=True,
    )
