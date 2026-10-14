"""shop force join + server status config fields

Revision ID: bb2cc3dd4ee5
Revises: aa1bb2cc3dd4
Create Date: 2026-10-14 13:30:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "bb2cc3dd4ee5"
down_revision = "aa1bb2cc3dd4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("shop_configs") as batch_op:
        batch_op.add_column(sa.Column("force_join_enabled", sa.Boolean(), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("force_join_channel_id", sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column("force_join_channel_url", sa.String(length=512), nullable=True))
        batch_op.add_column(sa.Column("server_status_enabled", sa.Boolean(), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("server_status_group_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("shop_configs") as batch_op:
        batch_op.drop_column("server_status_group_id")
        batch_op.drop_column("server_status_enabled")
        batch_op.drop_column("force_join_channel_url")
        batch_op.drop_column("force_join_channel_id")
        batch_op.drop_column("force_join_enabled")
