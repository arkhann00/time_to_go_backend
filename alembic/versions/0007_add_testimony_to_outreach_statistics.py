"""Add testimony to outreach_statistics.

Revision ID: 0007_add_testimony_to_outreach_statistics
Revises: 0006_single_statistics_per_user
Create Date: 2026-06-08
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0007_add_testimony_to_outreach_statistics"
down_revision = "0006_single_statistics_per_user"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("outreach_statistics") as batch_op:
        batch_op.add_column(sa.Column("testimony", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("outreach_statistics") as batch_op:
        batch_op.drop_column("testimony")
