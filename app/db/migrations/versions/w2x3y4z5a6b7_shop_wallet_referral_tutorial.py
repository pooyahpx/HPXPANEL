"""shop wallet referral tutorial fields

Revision ID: w2x3y4z5a6b7
Revises: v1w2x3y4z5a6
Create Date: 2026-09-28 04:50:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "w2x3y4z5a6b7"
down_revision = "v1w2x3y4z5a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("shop_configs") as batch_op:
        batch_op.add_column(sa.Column("wallet_enabled", sa.Boolean(), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("referral_enabled", sa.Boolean(), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("referral_reward_toman", sa.BigInteger(), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("referral_reward_data_gb", sa.Integer(), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("tutorial_enabled", sa.Boolean(), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("tutorial_text", sa.String(length=2000), nullable=True))
        batch_op.add_column(sa.Column("tutorial_url", sa.String(length=512), nullable=True))

    with op.batch_alter_table("telegram_profiles") as batch_op:
        batch_op.add_column(sa.Column("referral_code", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("referred_by_telegram_id", sa.BigInteger(), nullable=True))
        batch_op.add_column(sa.Column("referral_rewarded", sa.Boolean(), server_default="0", nullable=False))
        batch_op.create_index("ix_telegram_profiles_referred_by_telegram_id", ["referred_by_telegram_id"])
        batch_op.create_unique_constraint("uq_telegram_profiles_referral_code", ["referral_code"])

    op.create_table(
        "shop_buyer_wallets",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("admin_id", sa.BigInteger(), nullable=False),
        sa.Column("buyer_telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("balance_toman", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["admin_id"], ["admins.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("admin_id", "buyer_telegram_id", name="uq_shop_buyer_wallet"),
    )
    op.create_index("ix_shop_buyer_wallets_buyer_telegram_id", "shop_buyer_wallets", ["buyer_telegram_id"])

    op.create_table(
        "shop_wallet_ledger",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("admin_id", sa.BigInteger(), nullable=False),
        sa.Column("buyer_telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("amount_toman", sa.BigInteger(), nullable=False),
        sa.Column("kind", sa.String(length=32), server_default="adjust", nullable=False),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("order_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["admin_id"], ["admins.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["order_id"], ["shop_orders.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_shop_wallet_ledger_buyer_telegram_id", "shop_wallet_ledger", ["buyer_telegram_id"])


def downgrade() -> None:
    op.drop_index("ix_shop_wallet_ledger_buyer_telegram_id", table_name="shop_wallet_ledger")
    op.drop_table("shop_wallet_ledger")
    op.drop_index("ix_shop_buyer_wallets_buyer_telegram_id", table_name="shop_buyer_wallets")
    op.drop_table("shop_buyer_wallets")
    with op.batch_alter_table("telegram_profiles") as batch_op:
        batch_op.drop_constraint("uq_telegram_profiles_referral_code", type_="unique")
        batch_op.drop_index("ix_telegram_profiles_referred_by_telegram_id")
        batch_op.drop_column("referral_rewarded")
        batch_op.drop_column("referred_by_telegram_id")
        batch_op.drop_column("referral_code")
    with op.batch_alter_table("shop_configs") as batch_op:
        batch_op.drop_column("tutorial_url")
        batch_op.drop_column("tutorial_text")
        batch_op.drop_column("tutorial_enabled")
        batch_op.drop_column("referral_reward_data_gb")
        batch_op.drop_column("referral_reward_toman")
        batch_op.drop_column("referral_enabled")
        batch_op.drop_column("wallet_enabled")
