"""create budget ledger + custom price tiers

Revision ID: o4p5q6r7s8t9
Revises: n3o4p5q6r7s8
Create Date: 2026-09-09 22:40:00.000000

"""

import sqlalchemy as sa
from alembic import op

from app.db.compiles_types import SqliteCompatibleBigInteger

revision = "o4p5q6r7s8t9"
down_revision = "n3o4p5q6r7s8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "admins",
        sa.Column("create_budget_price_tiers", sa.JSON(), nullable=True),
    )
    op.create_table(
        "create_budget_ledger",
        sa.Column("id", SqliteCompatibleBigInteger(), autoincrement=True, nullable=False),
        sa.Column("admin_id", SqliteCompatibleBigInteger(), nullable=False),
        sa.Column("entry_type", sa.String(length=32), nullable=False),
        sa.Column("amount_toman", sa.BigInteger(), nullable=False),
        sa.Column("balance_after", sa.BigInteger(), nullable=False),
        sa.Column("actor_admin_id", SqliteCompatibleBigInteger(), nullable=True),
        sa.Column("user_id", SqliteCompatibleBigInteger(), nullable=True),
        sa.Column("username", sa.String(length=128), nullable=True),
        sa.Column("billable_gb", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("billable_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("price_per_gb", sa.BigInteger(), nullable=True),
        sa.Column("price_per_day", sa.BigInteger(), nullable=True),
        sa.Column("pricing_mode", sa.String(length=16), nullable=True),
        sa.Column("tier_gb", sa.Integer(), nullable=True),
        sa.Column("detail", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["admin_id"], ["admins.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_create_budget_ledger_admin_created",
        "create_budget_ledger",
        ["admin_id", "created_at"],
        unique=False,
    )
    op.create_index("ix_create_budget_ledger_entry_type", "create_budget_ledger", ["entry_type"], unique=False)
    op.create_index("ix_create_budget_ledger_user_id", "create_budget_ledger", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_create_budget_ledger_user_id", table_name="create_budget_ledger")
    op.drop_index("ix_create_budget_ledger_entry_type", table_name="create_budget_ledger")
    op.drop_index("ix_create_budget_ledger_admin_created", table_name="create_budget_ledger")
    op.drop_table("create_budget_ledger")
    op.drop_column("admins", "create_budget_price_tiers")
