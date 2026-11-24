"""Add host usage_coefficient and per-user host overrides.

Revision ID: gg7bb2cc3dd4
Revises: ff6aa1bb2cc3
Create Date: 2026-11-24 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "gg7bb2cc3dd4"
down_revision = "ff6aa1bb2cc3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "hosts",
        sa.Column("usage_coefficient", sa.Float(), server_default=sa.text("1.0"), nullable=False),
    )
    op.create_table(
        "user_host_coefficients",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("host_id", sa.BigInteger(), sa.ForeignKey("hosts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("usage_coefficient", sa.Float(), server_default=sa.text("1.0"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "host_id", name="uq_user_host_coefficients_user_host"),
    )
    op.create_index("ix_user_host_coefficients_user_id", "user_host_coefficients", ["user_id"])
    op.create_index("ix_user_host_coefficients_host_id", "user_host_coefficients", ["host_id"])


def downgrade() -> None:
    op.drop_index("ix_user_host_coefficients_host_id", table_name="user_host_coefficients")
    op.drop_index("ix_user_host_coefficients_user_id", table_name="user_host_coefficients")
    op.drop_table("user_host_coefficients")
    op.drop_column("hosts", "usage_coefficient")
