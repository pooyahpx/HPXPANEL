"""hpx pulse heal failover and icmp failback

Revision ID: r7s8t9u0v1w2
Revises: q6r7s8t9u0v1
Create Date: 2026-09-18 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "r7s8t9u0v1w2"
down_revision = "q6r7s8t9u0v1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("hpx_pulses", schema=None) as batch_op:
        batch_op.add_column(sa.Column("auto_heal_enabled", sa.Boolean(), nullable=False, server_default="1"))
        batch_op.add_column(sa.Column("last_heal_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("last_heal_action", sa.String(length=256), nullable=True))
        batch_op.add_column(sa.Column("heal_count_window", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("last_health_check", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("backup_pulse_id", sa.BigInteger(), nullable=True))
        batch_op.add_column(sa.Column("auto_failover", sa.Boolean(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("auto_failback", sa.Boolean(), nullable=False, server_default="1"))
        batch_op.add_column(sa.Column("failover_active", sa.Boolean(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("priority", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("last_failover_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_foreign_key(
            "fk_hpx_pulses_backup_pulse_id",
            "hpx_pulses",
            ["backup_pulse_id"],
            ["id"],
            ondelete="SET NULL",
        )

    with op.batch_alter_table("hpx_tunnels", schema=None) as batch_op:
        batch_op.add_column(sa.Column("auto_failback", sa.Boolean(), nullable=False, server_default="1"))
        batch_op.add_column(sa.Column("failover_active", sa.Boolean(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("failover_of_tunnel_id", sa.BigInteger(), nullable=True))
        batch_op.add_column(sa.Column("last_failover_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_foreign_key(
            "fk_hpx_tunnels_failover_of_tunnel_id",
            "hpx_tunnels",
            ["failover_of_tunnel_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("hpx_tunnels", schema=None) as batch_op:
        batch_op.drop_constraint("fk_hpx_tunnels_failover_of_tunnel_id", type_="foreignkey")
        batch_op.drop_column("last_failover_at")
        batch_op.drop_column("failover_of_tunnel_id")
        batch_op.drop_column("failover_active")
        batch_op.drop_column("auto_failback")

    with op.batch_alter_table("hpx_pulses", schema=None) as batch_op:
        batch_op.drop_constraint("fk_hpx_pulses_backup_pulse_id", type_="foreignkey")
        batch_op.drop_column("last_failover_at")
        batch_op.drop_column("priority")
        batch_op.drop_column("failover_active")
        batch_op.drop_column("auto_failback")
        batch_op.drop_column("auto_failover")
        batch_op.drop_column("backup_pulse_id")
        batch_op.drop_column("last_health_check")
        batch_op.drop_column("heal_count_window")
        batch_op.drop_column("last_heal_action")
        batch_op.drop_column("last_heal_at")
        batch_op.drop_column("auto_heal_enabled")
