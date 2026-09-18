"""shop custom purchase pricing + order snapshot

Revision ID: s8t9u0v1w2x3
Revises: r7s8t9u0v1w2
Create Date: 2026-09-18 22:15:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.db.compiles_types import SqliteCompatibleBigInteger

revision = "s8t9u0v1w2x3"
down_revision = "r7s8t9u0v1w2"
branch_labels = None
depends_on = None

JSONB = sa.JSON().with_variant(postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    op.add_column(
        "shop_configs",
        sa.Column("custom_enabled", sa.Boolean(), nullable=False, server_default="0"),
    )
    op.add_column(
        "shop_configs",
        sa.Column("custom_price_per_gb", sa.BigInteger(), nullable=False, server_default="0"),
    )
    op.add_column(
        "shop_configs",
        sa.Column("custom_price_per_day", sa.BigInteger(), nullable=False, server_default="0"),
    )
    op.add_column(
        "shop_configs",
        sa.Column("custom_price_per_ip", sa.BigInteger(), nullable=False, server_default="0"),
    )
    op.add_column(
        "shop_configs",
        sa.Column("custom_min_gb", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "shop_configs",
        sa.Column("custom_max_gb", sa.Integer(), nullable=False, server_default="500"),
    )
    op.add_column(
        "shop_configs",
        sa.Column("custom_min_days", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "shop_configs",
        sa.Column("custom_max_days", sa.Integer(), nullable=False, server_default="365"),
    )
    op.add_column(
        "shop_configs",
        sa.Column("custom_base_ip", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column("shop_configs", sa.Column("custom_group_ids", JSONB, nullable=True))

    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("shop_orders") as batch_op:
            batch_op.alter_column(
                "plan_id",
                existing_type=SqliteCompatibleBigInteger(),
                nullable=True,
            )
    else:
        op.alter_column("shop_orders", "plan_id", existing_type=sa.BigInteger(), nullable=True)

    op.add_column("shop_orders", sa.Column("requested_username", sa.String(length=128), nullable=True))
    op.add_column("shop_orders", sa.Column("custom_data_gb", sa.Integer(), nullable=True))
    op.add_column("shop_orders", sa.Column("custom_expire_days", sa.Integer(), nullable=True))
    op.add_column("shop_orders", sa.Column("custom_ip_limit", sa.Integer(), nullable=True))
    op.add_column("shop_orders", sa.Column("quoted_price_toman", sa.BigInteger(), nullable=True))
    op.add_column(
        "shop_orders",
        sa.Column("is_custom", sa.Boolean(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("shop_orders", "is_custom")
    op.drop_column("shop_orders", "quoted_price_toman")
    op.drop_column("shop_orders", "custom_ip_limit")
    op.drop_column("shop_orders", "custom_expire_days")
    op.drop_column("shop_orders", "custom_data_gb")
    op.drop_column("shop_orders", "requested_username")

    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("shop_orders") as batch_op:
            batch_op.alter_column(
                "plan_id",
                existing_type=SqliteCompatibleBigInteger(),
                nullable=False,
            )
    else:
        op.alter_column("shop_orders", "plan_id", existing_type=sa.BigInteger(), nullable=False)

    op.drop_column("shop_configs", "custom_group_ids")
    op.drop_column("shop_configs", "custom_base_ip")
    op.drop_column("shop_configs", "custom_max_days")
    op.drop_column("shop_configs", "custom_min_days")
    op.drop_column("shop_configs", "custom_max_gb")
    op.drop_column("shop_configs", "custom_min_gb")
    op.drop_column("shop_configs", "custom_price_per_ip")
    op.drop_column("shop_configs", "custom_price_per_day")
    op.drop_column("shop_configs", "custom_price_per_gb")
    op.drop_column("shop_configs", "custom_enabled")
