"""telegram sub deliveries

Revision ID: h9i0j1k2l3m4
Revises: g8h9i0j1k2l3
Create Date: 2026-08-22 18:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "h9i0j1k2l3m4"
down_revision = "g8h9i0j1k2l3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "telegram_sub_deliveries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("buyer_telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("source_type", sa.String(length=16), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("panel_username", sa.String(length=128), nullable=False),
        sa.Column("sub_version", sa.String(length=64), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_telegram_sub_deliveries_buyer_telegram_id", "telegram_sub_deliveries", ["buyer_telegram_id"])


def downgrade() -> None:
    op.drop_index("ix_telegram_sub_deliveries_buyer_telegram_id", table_name="telegram_sub_deliveries")
    op.drop_table("telegram_sub_deliveries")
