"""shop multi cards and one-time test config

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-08-14 12:00:00.000000

"""

import json

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "f6a7b8c9d0e1"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None

JSONB = sa.JSON().with_variant(postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    op.add_column("shop_configs", sa.Column("cards", JSONB, nullable=True))
    op.add_column(
        "shop_configs",
        sa.Column("test_enabled", sa.Boolean(), nullable=False, server_default="0"),
    )
    op.add_column(
        "shop_configs",
        sa.Column("test_data_limit", sa.BigInteger(), nullable=False, server_default="1073741824"),
    )
    op.add_column(
        "shop_configs",
        sa.Column("test_expire_days", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "shop_configs",
        sa.Column("test_group_ids", JSONB, nullable=True),
    )
    op.add_column(
        "telegram_profiles",
        sa.Column("test_claimed", sa.Boolean(), nullable=False, server_default="0"),
    )

    conn = op.get_bind()
    rows = conn.execute(
        sa.text(
            "SELECT admin_id, card_number, card_holder FROM shop_configs "
            "WHERE card_number IS NOT NULL AND card_number != ''"
        )
    ).fetchall()
    for admin_id, card_number, card_holder in rows:
        cards = json.dumps([{"number": card_number, "holder": card_holder or ""}])
        conn.execute(
            sa.text("UPDATE shop_configs SET cards = :cards WHERE admin_id = :admin_id"),
            {"cards": cards, "admin_id": admin_id},
        )


def downgrade() -> None:
    op.drop_column("telegram_profiles", "test_claimed")
    op.drop_column("shop_configs", "test_group_ids")
    op.drop_column("shop_configs", "test_expire_days")
    op.drop_column("shop_configs", "test_data_limit")
    op.drop_column("shop_configs", "test_enabled")
    op.drop_column("shop_configs", "cards")
