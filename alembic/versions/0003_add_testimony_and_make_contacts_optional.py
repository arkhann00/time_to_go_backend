"""Add testimony field and remove contact requirement.

Revision ID: 0003_add_testimony_and_make_contacts_optional
Revises: 0002_update_christian_stage_values
Create Date: 2026-05-14 16:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0003_add_testimony_and_make_contacts_optional"
down_revision = "0002_update_christian_stage_values"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("believers", recreate="always") as batch_op:
        batch_op.add_column(sa.Column("testimony", sa.Text(), nullable=True))
        batch_op.drop_constraint("ck_believers_contact_exists", type_="check")


def downgrade() -> None:
    # Required for restoring contact constraint on existing data.
    op.execute(
        sa.text(
            "UPDATE believers "
            "SET telegram = 'unknown' "
            "WHERE telegram IS NULL AND phone_number IS NULL"
        )
    )

    with op.batch_alter_table("believers", recreate="always") as batch_op:
        batch_op.create_check_constraint(
            "ck_believers_contact_exists",
            "telegram IS NOT NULL OR phone_number IS NOT NULL",
        )
        batch_op.drop_column("testimony")
