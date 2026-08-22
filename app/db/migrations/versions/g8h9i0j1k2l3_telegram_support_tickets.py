"""telegram support tickets

Revision ID: g8h9i0j1k2l3
Revises: f7a8b9c0d1e2
Create Date: 2026-08-22 17:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

from app.db.compiles_types import SqliteCompatibleBigInteger

revision = "g8h9i0j1k2l3"
down_revision = "f7a8b9c0d1e2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "telegram_support_tickets",
        sa.Column("buyer_telegram_id", SqliteCompatibleBigInteger(), primary_key=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="open"),
        sa.Column("handler_admin_id", SqliteCompatibleBigInteger(), nullable=True),
        sa.Column("handler_username", sa.String(length=64), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )


def downgrade() -> None:
    op.drop_table("telegram_support_tickets")
