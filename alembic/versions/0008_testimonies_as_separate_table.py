"""Testimonies as separate table.

Revision ID: 0008_testimonies_as_separate_table
Revises: 0007_add_testimony_to_outreach_statistics
Create Date: 2026-06-08
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0008_testimonies_as_separate_table"
down_revision = "0007_add_testimony_to_outreach_statistics"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "testimonies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("outreach_statistics_id", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["outreach_statistics_id"],
            ["outreach_statistics.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_testimonies_outreach_statistics_id"),
        "testimonies",
        ["outreach_statistics_id"],
        unique=False,
    )

    # Migrate existing testimony data
    connection = op.get_bind()
    rows = connection.execute(
        sa.text("SELECT id, testimony FROM outreach_statistics WHERE testimony IS NOT NULL")
    ).fetchall()
    if rows:
        connection.execute(
            sa.text(
                "INSERT INTO testimonies (outreach_statistics_id, text) VALUES (:stats_id, :text)"
            ),
            [{"stats_id": row[0], "text": row[1]} for row in rows],
        )

    with op.batch_alter_table("outreach_statistics") as batch_op:
        batch_op.drop_column("testimony")


def downgrade() -> None:
    with op.batch_alter_table("outreach_statistics") as batch_op:
        batch_op.add_column(sa.Column("testimony", sa.Text(), nullable=True))

    connection = op.get_bind()
    rows = connection.execute(
        sa.text(
            "SELECT outreach_statistics_id, text FROM testimonies ORDER BY created_at DESC"
        )
    ).fetchall()
    for row in rows:
        connection.execute(
            sa.text(
                "UPDATE outreach_statistics SET testimony = :text WHERE id = :stats_id AND testimony IS NULL"
            ),
            {"text": row[1], "stats_id": row[0]},
        )

    op.drop_index(
        op.f("ix_testimonies_outreach_statistics_id"), table_name="testimonies"
    )
    op.drop_table("testimonies")
