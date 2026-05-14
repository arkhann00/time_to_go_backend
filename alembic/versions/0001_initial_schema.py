"""Initial schema with users, methods, and believers.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-05-14 15:10:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None

christian_stage_enum = sa.Enum(
    "INTERESTED_IN_FAITH",
    "ACCEPTED_JESUS",
    "CAME_TO_CHURCH",
    "BAPTIZED",
    "PREACHES_GOSPEL",
    name="christianstage",
)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("avatar_url", sa.String(length=500), nullable=True),
        sa.Column("about", sa.String(length=1000), nullable=True),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "evangelism_methods",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.UniqueConstraint("user_id", "name", name="uq_method_user_name"),
    )

    op.create_table(
        "believers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("telegram", sa.String(length=255), nullable=True),
        sa.Column("phone_number", sa.String(length=64), nullable=True),
        sa.Column("met_at", sa.Date(), nullable=False),
        sa.Column("stage", christian_stage_enum, nullable=False),
        sa.Column("method_id", sa.Integer(), sa.ForeignKey("evangelism_methods.id"), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint(
            "telegram IS NOT NULL OR phone_number IS NOT NULL",
            name="ck_believers_contact_exists",
        ),
    )
    op.create_index("ix_believers_user_id", "believers", ["user_id"], unique=False)

    methods_table = sa.table(
        "evangelism_methods",
        sa.column("name", sa.String),
        sa.column("is_default", sa.Boolean),
        sa.column("user_id", sa.Integer),
    )
    op.bulk_insert(
        methods_table,
        [
            {"name": "4 знака", "is_default": True, "user_id": None},
            {"name": "Иисус у двери", "is_default": True, "user_id": None},
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_believers_user_id", table_name="believers")
    op.drop_table("believers")
    op.drop_table("evangelism_methods")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    christian_stage_enum.drop(op.get_bind(), checkfirst=True)

