"""add per-admin create budget fields

Revision ID: m2n3o4p5q6r7
Revises: l1m2n3o4p5q6
Create Date: 2026-09-09 11:40:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "m2n3o4p5q6r7"
down_revision = "l1m2n3o4p5q6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "admins",
        sa.Column("create_budget_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "admins",
        sa.Column("create_budget_toman", sa.BigInteger(), nullable=False, server_default="0"),
    )
    op.add_column(
        "admins",
        sa.Column("create_budget_price_per_gb", sa.BigInteger(), nullable=False, server_default="0"),
    )
    op.add_column(
        "admins",
        sa.Column("create_budget_price_per_day", sa.BigInteger(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("admins", "create_budget_price_per_day")
    op.drop_column("admins", "create_budget_price_per_gb")
    op.drop_column("admins", "create_budget_toman")
    op.drop_column("admins", "create_budget_enabled")
