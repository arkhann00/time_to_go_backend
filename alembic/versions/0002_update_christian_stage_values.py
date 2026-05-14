"""Change believer stage enum values to English.

Revision ID: 0002_update_christian_stage_values
Revises: 0001_initial_schema
Create Date: 2026-05-14 15:50:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0002_update_christian_stage_values"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None

OLD_STAGE_ENUM = sa.Enum(
    "INTERESTED_IN_FAITH",
    "ACCEPTED_JESUS",
    "CAME_TO_CHURCH",
    "BAPTIZED",
    "PREACHES_GOSPEL",
    name="christianstage",
)

NEW_STAGE_ENUM = sa.Enum(
    "interested",
    "receivedJesus",
    "joinedCommunity",
    "baptised",
    "evangelist",
    name="christianstage",
    native_enum=False,
)

OLD_TO_NEW = {
    "INTERESTED_IN_FAITH": "interested",
    "ACCEPTED_JESUS": "receivedJesus",
    "CAME_TO_CHURCH": "joinedCommunity",
    "BAPTIZED": "baptised",
    "PREACHES_GOSPEL": "evangelist",
}

NEW_TO_OLD = {value: key for key, value in OLD_TO_NEW.items()}


def upgrade() -> None:
    for old_value, new_value in OLD_TO_NEW.items():
        op.execute(
            sa.text("UPDATE believers SET stage = :new_value WHERE stage = :old_value").bindparams(
                new_value=new_value,
                old_value=old_value,
            )
        )

    with op.batch_alter_table("believers", recreate="always") as batch_op:
        batch_op.alter_column(
            "stage",
            existing_type=OLD_STAGE_ENUM,
            type_=NEW_STAGE_ENUM,
            existing_nullable=False,
            nullable=False,
        )


def downgrade() -> None:
    for new_value, old_value in NEW_TO_OLD.items():
        op.execute(
            sa.text("UPDATE believers SET stage = :old_value WHERE stage = :new_value").bindparams(
                old_value=old_value,
                new_value=new_value,
            )
        )

    with op.batch_alter_table("believers", recreate="always") as batch_op:
        batch_op.alter_column(
            "stage",
            existing_type=NEW_STAGE_ENUM,
            type_=OLD_STAGE_ENUM,
            existing_nullable=False,
            nullable=False,
        )

