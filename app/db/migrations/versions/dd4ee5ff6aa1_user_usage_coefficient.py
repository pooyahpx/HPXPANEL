"""Add per-user usage_coefficient for traffic multiplier.

Revision ID: dd4ee5ff6aa1
Revises: cc3dd4ee5ff6
Create Date: 2026-11-09 19:10:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "dd4ee5ff6aa1"
down_revision = "cc3dd4ee5ff6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("usage_coefficient", sa.Float(), server_default=sa.text("1.0"), nullable=False)
        )


def downgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("usage_coefficient")
