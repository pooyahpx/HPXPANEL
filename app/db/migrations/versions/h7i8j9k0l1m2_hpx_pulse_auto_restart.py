"""hpx pulse auto-restart interval

Revision ID: h7i8j9k0l1m2
Revises: g6h7i8j9k0l1
Create Date: 2026-09-04 01:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "h7i8j9k0l1m2"
down_revision = "g6h7i8j9k0l1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("hpx_pulses", schema=None) as batch_op:
        batch_op.add_column(sa.Column("auto_restart_interval_minutes", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("last_auto_restart_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("hpx_pulses", schema=None) as batch_op:
        batch_op.drop_column("last_auto_restart_at")
        batch_op.drop_column("auto_restart_interval_minutes")
