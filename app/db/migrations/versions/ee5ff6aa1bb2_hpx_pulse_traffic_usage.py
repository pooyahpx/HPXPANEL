"""Add HPX Pulse traffic counters and usage samples.

Revision ID: ee5ff6aa1bb2
Revises: dd4ee5ff6aa1
Create Date: 2026-11-12 22:55:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "ee5ff6aa1bb2"
down_revision = "dd4ee5ff6aa1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("hpx_pulses", schema=None) as batch_op:
        batch_op.add_column(sa.Column("bytes_up", sa.BigInteger(), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("bytes_down", sa.BigInteger(), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("last_iface_rx", sa.BigInteger(), nullable=True))
        batch_op.add_column(sa.Column("last_iface_tx", sa.BigInteger(), nullable=True))
        batch_op.add_column(sa.Column("last_traffic_side", sa.String(length=8), nullable=True))

    op.create_table(
        "hpx_pulse_usages",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("pulse_id", sa.BigInteger(), nullable=False),
        sa.Column("uplink", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("downlink", sa.BigInteger(), server_default="0", nullable=False),
        sa.ForeignKeyConstraint(["pulse_id"], ["hpx_pulses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("created_at", "pulse_id"),
    )
    op.create_index("ix_hpx_pulse_usages_created_at", "hpx_pulse_usages", ["created_at"])
    op.create_index("ix_hpx_pulse_usages_pulse_id_created_at", "hpx_pulse_usages", ["pulse_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_hpx_pulse_usages_pulse_id_created_at", table_name="hpx_pulse_usages")
    op.drop_index("ix_hpx_pulse_usages_created_at", table_name="hpx_pulse_usages")
    op.drop_table("hpx_pulse_usages")
    with op.batch_alter_table("hpx_pulses", schema=None) as batch_op:
        batch_op.drop_column("last_traffic_side")
        batch_op.drop_column("last_iface_tx")
        batch_op.drop_column("last_iface_rx")
        batch_op.drop_column("bytes_down")
        batch_op.drop_column("bytes_up")
