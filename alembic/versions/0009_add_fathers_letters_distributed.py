"""Add fathers_letters_distributed to outreach_statistics.

Revision ID: 0009_add_fathers_letters_distributed
Revises: 0008_testimonies_as_separate_table
Create Date: 2026-06-09
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0009_add_fathers_letters_distributed"
down_revision = "0008_testimonies_as_separate_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("outreach_statistics") as batch_op:
        batch_op.add_column(
            sa.Column(
                "fathers_letters_distributed",
                sa.Integer(),
                nullable=False,
                server_default="0",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("outreach_statistics") as batch_op:
        batch_op.drop_column("fathers_letters_distributed")
