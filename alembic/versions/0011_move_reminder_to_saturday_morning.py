"""Move the weekly push reminder to Saturday at 10:00.

Revision ID: 0011_move_reminder_to_saturday_morning
Revises: 0010_add_push_notifications
Create Date: 2026-08-26
"""

from alembic import op

revision = "0011_move_reminder_to_saturday_morning"
down_revision = "0010_add_push_notifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Apply the new default to users whose settings already exist as well.
    op.execute(
        "UPDATE notification_settings "
        "SET believers_friday_reminder_time = '10:00:00'"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE notification_settings "
        "SET believers_friday_reminder_time = '18:00:00'"
    )
