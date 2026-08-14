"""user group quotas

Revision ID: f7a8b9c0d1e2
Revises: f6a7b8c9d0e1
Create Date: 2026-08-14 13:10:00.000000

"""

import sqlalchemy as sa
from alembic import op

from app.db.compiles_types import SqliteCompatibleBigInteger

revision = "f7a8b9c0d1e2"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_group_quotas",
        sa.Column("id", SqliteCompatibleBigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", SqliteCompatibleBigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("group_id", SqliteCompatibleBigInteger(), sa.ForeignKey("groups.id", ondelete="CASCADE"), nullable=False),
        sa.Column("data_limit", sa.BigInteger(), nullable=True),
        sa.Column("used_traffic", sa.BigInteger(), nullable=False, server_default="0"),
        sa.UniqueConstraint("user_id", "group_id", name="uq_user_group_quotas_user_group"),
    )
    op.create_index("ix_user_group_quotas_user_id", "user_group_quotas", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_user_group_quotas_user_id", table_name="user_group_quotas")
    op.drop_table("user_group_quotas")
