"""hpx icmp tunnels

Revision ID: i0j1k2l3m4n5
Revises: h9i0j1k2l3m4
Create Date: 2026-08-26 02:30:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "i0j1k2l3m4n5"
down_revision = "h9i0j1k2l3m4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "hpx_tunnels",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("role", sa.Enum("iran", "foreign", name="hpxtunnelrole"), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "running",
                "stopped",
                "starting",
                "stopping",
                "error",
                "unhealthy",
                name="hpxtunnelstatus",
            ),
            nullable=False,
            server_default="stopped",
        ),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("remote_ip", sa.String(length=45), nullable=True),
        sa.Column("server_listen", sa.String(length=45), nullable=False, server_default="0.0.0.0"),
        sa.Column("password_encrypted", sa.String(length=512), nullable=False),
        sa.Column("interface", sa.String(length=32), nullable=False, server_default="hpx0"),
        sa.Column("local_ip", sa.String(length=45), nullable=False, server_default="10.200.200.2"),
        sa.Column("subnet", sa.String(length=64), nullable=False, server_default="10.200.200.0/24"),
        sa.Column("mtu", sa.Integer(), nullable=True),
        sa.Column("keepalive", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("dscp_mark", sa.Integer(), nullable=True),
        sa.Column("bandwidth_limit", sa.String(length=32), nullable=True),
        sa.Column("operating_mode", sa.String(length=64), nullable=True),
        sa.Column("port_forwards", sa.JSON(), nullable=True),
        sa.Column("docker_image", sa.String(length=128), nullable=False, server_default="ghcr.io/pooyahpx/hpx-icmp:0.0.3"),
        sa.Column("container_name", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("backup_tunnel_id", sa.BigInteger(), sa.ForeignKey("hpx_tunnels.id", ondelete="SET NULL"), nullable=True),
        sa.Column("auto_failover", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("alert_on_down", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("note", sa.String(length=512), nullable=True),
        sa.Column("last_health_check", sa.DateTime(timezone=True), nullable=True),
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.Column("packet_loss_pct", sa.Float(), nullable=True),
        sa.Column("message", sa.String(length=1024), nullable=True),
        sa.Column("bytes_up", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("bytes_down", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("last_status_change", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )


def downgrade() -> None:
    op.drop_table("hpx_tunnels")
