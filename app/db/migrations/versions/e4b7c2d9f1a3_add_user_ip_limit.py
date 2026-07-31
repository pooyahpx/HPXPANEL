"""add user ip_limit for concurrent IP limiting

Revision ID: e4b7c2d9f1a3
Revises: d3a8f6c1e4b2
Create Date: 2026-07-31 03:20:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "e4b7c2d9f1a3"
down_revision = "d3a8f6c1e4b2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("ip_limit", sa.BigInteger(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "ip_limit")
