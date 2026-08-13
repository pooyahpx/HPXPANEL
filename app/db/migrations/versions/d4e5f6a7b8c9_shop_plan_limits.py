"""shop plan ip_limit and hwid_limit

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-08-13 17:45:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("shop_plans", sa.Column("ip_limit", sa.Integer(), nullable=True))
    op.add_column("shop_plans", sa.Column("hwid_limit", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("shop_plans", "hwid_limit")
    op.drop_column("shop_plans", "ip_limit")
