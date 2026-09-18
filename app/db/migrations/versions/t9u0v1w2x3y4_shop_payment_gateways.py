"""shop payment gateways (zarinpal, idpay, nowpayments, paypal, stripe)

Revision ID: t9u0v1w2x3y4
Revises: s8t9u0v1w2x3
Create Date: 2026-09-19 01:20:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "t9u0v1w2x3y4"
down_revision = "s8t9u0v1w2x3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "shop_configs",
        sa.Column("pay_card_enabled", sa.Boolean(), nullable=False, server_default="1"),
    )
    op.add_column(
        "shop_configs",
        sa.Column("pay_zarinpal_enabled", sa.Boolean(), nullable=False, server_default="0"),
    )
    op.add_column("shop_configs", sa.Column("pay_zarinpal_merchant_id", sa.String(length=64), nullable=True))
    op.add_column(
        "shop_configs",
        sa.Column("pay_zarinpal_sandbox", sa.Boolean(), nullable=False, server_default="0"),
    )
    op.add_column(
        "shop_configs",
        sa.Column("pay_idpay_enabled", sa.Boolean(), nullable=False, server_default="0"),
    )
    op.add_column("shop_configs", sa.Column("pay_idpay_api_key", sa.String(length=128), nullable=True))
    op.add_column(
        "shop_configs",
        sa.Column("pay_idpay_sandbox", sa.Boolean(), nullable=False, server_default="1"),
    )
    op.add_column(
        "shop_configs",
        sa.Column("pay_nowpayments_enabled", sa.Boolean(), nullable=False, server_default="0"),
    )
    op.add_column("shop_configs", sa.Column("pay_nowpayments_api_key", sa.String(length=128), nullable=True))
    op.add_column("shop_configs", sa.Column("pay_nowpayments_ipn_secret", sa.String(length=128), nullable=True))
    op.add_column(
        "shop_configs",
        sa.Column("pay_paypal_enabled", sa.Boolean(), nullable=False, server_default="0"),
    )
    op.add_column("shop_configs", sa.Column("pay_paypal_client_id", sa.String(length=128), nullable=True))
    op.add_column("shop_configs", sa.Column("pay_paypal_client_secret", sa.String(length=128), nullable=True))
    op.add_column(
        "shop_configs",
        sa.Column("pay_paypal_sandbox", sa.Boolean(), nullable=False, server_default="1"),
    )
    op.add_column(
        "shop_configs",
        sa.Column("pay_stripe_enabled", sa.Boolean(), nullable=False, server_default="0"),
    )
    op.add_column("shop_configs", sa.Column("pay_stripe_secret_key", sa.String(length=256), nullable=True))
    op.add_column("shop_configs", sa.Column("pay_stripe_webhook_secret", sa.String(length=256), nullable=True))
    op.add_column("shop_configs", sa.Column("pay_callback_base_url", sa.String(length=512), nullable=True))

    op.add_column("shop_orders", sa.Column("payment_method", sa.String(length=32), nullable=True))
    op.add_column("shop_orders", sa.Column("payment_ref", sa.String(length=128), nullable=True))
    op.add_column("shop_orders", sa.Column("payment_url", sa.String(length=1024), nullable=True))
    op.add_column(
        "shop_orders",
        sa.Column("payment_paid", sa.Boolean(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("shop_orders", "payment_paid")
    op.drop_column("shop_orders", "payment_url")
    op.drop_column("shop_orders", "payment_ref")
    op.drop_column("shop_orders", "payment_method")

    op.drop_column("shop_configs", "pay_callback_base_url")
    op.drop_column("shop_configs", "pay_stripe_webhook_secret")
    op.drop_column("shop_configs", "pay_stripe_secret_key")
    op.drop_column("shop_configs", "pay_stripe_enabled")
    op.drop_column("shop_configs", "pay_paypal_sandbox")
    op.drop_column("shop_configs", "pay_paypal_client_secret")
    op.drop_column("shop_configs", "pay_paypal_client_id")
    op.drop_column("shop_configs", "pay_paypal_enabled")
    op.drop_column("shop_configs", "pay_nowpayments_ipn_secret")
    op.drop_column("shop_configs", "pay_nowpayments_api_key")
    op.drop_column("shop_configs", "pay_nowpayments_enabled")
    op.drop_column("shop_configs", "pay_idpay_sandbox")
    op.drop_column("shop_configs", "pay_idpay_api_key")
    op.drop_column("shop_configs", "pay_idpay_enabled")
    op.drop_column("shop_configs", "pay_zarinpal_sandbox")
    op.drop_column("shop_configs", "pay_zarinpal_merchant_id")
    op.drop_column("shop_configs", "pay_zarinpal_enabled")
    op.drop_column("shop_configs", "pay_card_enabled")
