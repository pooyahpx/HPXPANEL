"""add telegram shop tables

Revision ID: a7b8c9d0e1f2
Revises: f1a2b3c4d5e6
Create Date: 2026-08-12 20:15:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "a7b8c9d0e1f2"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None

JSONB = sa.JSON().with_variant(postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    op.create_table(
        "telegram_profiles",
        sa.Column("telegram_id", sa.BigInteger(), primary_key=True),
        sa.Column("lang", sa.String(length=8), nullable=False, server_default="fa"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "shop_configs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("admin_id", sa.BigInteger(), sa.ForeignKey("admins.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("card_number", sa.String(length=64), nullable=True),
        sa.Column("card_holder", sa.String(length=128), nullable=True),
        sa.Column("welcome_note", sa.String(length=500), nullable=True),
    )

    op.create_table(
        "shop_plans",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("admin_id", sa.BigInteger(), sa.ForeignKey("admins.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("data_limit", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("expire_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("price_toman", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("group_ids", JSONB, nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
    )

    shop_order_status = sa.Enum("pending", "approved", "rejected", name="shoporderstatus", create_constraint=True)
    shop_order_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "shop_orders",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("plan_id", sa.BigInteger(), sa.ForeignKey("shop_plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("admin_id", sa.BigInteger(), sa.ForeignKey("admins.id", ondelete="CASCADE"), nullable=False),
        sa.Column("buyer_telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("buyer_username", sa.String(length=64), nullable=True),
        sa.Column("status", shop_order_status, nullable=False, server_default="pending"),
        sa.Column("receipt_file_id", sa.String(length=256), nullable=True),
        sa.Column("created_user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("note", sa.String(length=500), nullable=True),
    )
    op.create_index("ix_shop_orders_buyer_telegram_id", "shop_orders", ["buyer_telegram_id"])


def downgrade() -> None:
    op.drop_index("ix_shop_orders_buyer_telegram_id", table_name="shop_orders")
    op.drop_table("shop_orders")
    op.drop_table("shop_plans")
    op.drop_table("shop_configs")
    op.drop_table("telegram_profiles")
    sa.Enum(name="shoporderstatus").drop(op.get_bind(), checkfirst=True)
