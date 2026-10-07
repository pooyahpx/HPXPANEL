"""shop discount codes + order discount fields

Revision ID: aa1bb2cc3dd4
Revises: z5a6b7c8d9e0
Create Date: 2026-10-07 18:10:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "aa1bb2cc3dd4"
down_revision = "z5a6b7c8d9e0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "shop_discount_codes",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("admin_id", sa.BigInteger(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("percent_off", sa.Integer(), nullable=True),
        sa.Column("amount_off_toman", sa.BigInteger(), nullable=True),
        sa.Column("max_uses", sa.Integer(), nullable=True),
        sa.Column("used_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["admin_id"], ["admins.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("admin_id", "code", name="uq_shop_discount_admin_code"),
    )
    op.create_index("ix_shop_discount_codes_admin_id", "shop_discount_codes", ["admin_id"])

    with op.batch_alter_table("shop_orders") as batch_op:
        batch_op.add_column(sa.Column("discount_code", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("discount_amount_toman", sa.BigInteger(), nullable=True))
        batch_op.add_column(sa.Column("original_price_toman", sa.BigInteger(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("shop_orders") as batch_op:
        batch_op.drop_column("original_price_toman")
        batch_op.drop_column("discount_amount_toman")
        batch_op.drop_column("discount_code")
    op.drop_index("ix_shop_discount_codes_admin_id", table_name="shop_discount_codes")
    op.drop_table("shop_discount_codes")
