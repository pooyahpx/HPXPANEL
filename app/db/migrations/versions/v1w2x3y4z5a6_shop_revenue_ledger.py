"""shop revenue ledger for paid gateway/card sales

Revision ID: v1w2x3y4z5a6
Revises: u0v1w2x3y4z5
Create Date: 2026-09-19 04:40:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "v1w2x3y4z5a6"
down_revision = "u0v1w2x3y4z5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "shop_revenue_ledger",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("admin_id", sa.BigInteger(), nullable=False),
        sa.Column("order_id", sa.BigInteger(), nullable=False),
        sa.Column("entry_type", sa.String(length=32), nullable=False),
        sa.Column("amount_toman", sa.BigInteger(), nullable=False),
        sa.Column("payment_method", sa.String(length=32), nullable=False),
        sa.Column("payment_ref", sa.String(length=128), nullable=True),
        sa.Column("buyer_telegram_id", sa.BigInteger(), nullable=True),
        sa.Column("username", sa.String(length=128), nullable=True),
        sa.Column("detail", sa.String(length=500), nullable=True),
        sa.Column("settled_with_owner", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("settled_by_admin_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["admin_id"], ["admins.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["order_id"], ["shop_orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id", name="uq_shop_revenue_ledger_order_id"),
    )
    op.create_index("ix_shop_revenue_ledger_admin_created", "shop_revenue_ledger", ["admin_id", "created_at"])
    op.create_index("ix_shop_revenue_ledger_payment_method", "shop_revenue_ledger", ["payment_method"])
    op.add_column(
        "telegram_profiles",
        sa.Column("preferred_shop_admin_id", sa.BigInteger(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("telegram_profiles", "preferred_shop_admin_id")
    op.drop_index("ix_shop_revenue_ledger_payment_method", table_name="shop_revenue_ledger")
    op.drop_index("ix_shop_revenue_ledger_admin_created", table_name="shop_revenue_ledger")
    op.drop_table("shop_revenue_ledger")
