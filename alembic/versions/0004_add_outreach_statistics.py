"""Add outreach statistics table.

Revision ID: 0004_add_outreach_statistics
Revises: 0003_add_testimony_and_make_contacts_optional
Create Date: 2026-06-04 12:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0004_add_outreach_statistics"
down_revision = "0003_add_testimony_and_make_contacts_optional"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "outreach_statistics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("gospels_told", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "salvation_prayed_unreachable",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "scriptures_distributed",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "healings_deliverances",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_outreach_statistics_user_id",
        "outreach_statistics",
        ["user_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_outreach_statistics_user_id", table_name="outreach_statistics")
    op.drop_table("outreach_statistics")
