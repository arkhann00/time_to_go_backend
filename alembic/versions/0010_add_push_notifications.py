"""Add push devices, notification settings and delivery journal.

Revision ID: 0010_add_push_notifications
Revises: 0009_add_fathers_letters_distributed
Create Date: 2026-08-24
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0010_add_push_notifications"
down_revision = "0009_add_fathers_letters_distributed"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "push_devices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token", sa.String(length=4096), nullable=False),
        sa.Column("platform", sa.String(length=7), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default="1", nullable=False),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token", name="uq_push_devices_token"),
    )
    op.create_index("ix_push_devices_user_id", "push_devices", ["user_id"])
    op.create_table(
        "notification_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "believers_friday_reminder_enabled",
            sa.Boolean(),
            server_default="1",
            nullable=False,
        ),
        sa.Column(
            "believers_friday_reminder_time",
            sa.Time(),
            server_default="18:00",
            nullable=False,
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_notification_settings_user_id"),
    )
    op.create_index(
        "ix_notification_settings_user_id", "notification_settings", ["user_id"]
    )
    op.execute("INSERT INTO notification_settings (user_id) SELECT id FROM users")
    op.create_table(
        "notification_deliveries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("notification_type", sa.String(length=100), nullable=False),
        sa.Column("local_date", sa.Date(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "notification_type",
            "local_date",
            name="uq_notification_delivery_user_type_date",
        ),
    )
    op.create_index(
        "ix_notification_deliveries_user_id", "notification_deliveries", ["user_id"]
    )


def downgrade() -> None:
    op.drop_index(
        "ix_notification_deliveries_user_id", table_name="notification_deliveries"
    )
    op.drop_table("notification_deliveries")
    op.drop_index(
        "ix_notification_settings_user_id", table_name="notification_settings"
    )
    op.drop_table("notification_settings")
    op.drop_index("ix_push_devices_user_id", table_name="push_devices")
    op.drop_table("push_devices")
