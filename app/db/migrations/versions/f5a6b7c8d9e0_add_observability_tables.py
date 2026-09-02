"""add observability tables

Revision ID: f5a6b7c8d9e0
Revises: e4f5a6b7c8d9
Create Date: 2026-09-02 03:30:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "f5a6b7c8d9e0"
down_revision = "e4f5a6b7c8d9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "system_stats",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("mem_total", sa.BigInteger(), nullable=False),
        sa.Column("mem_used", sa.BigInteger(), nullable=False),
        sa.Column("cpu_cores", sa.Integer(), nullable=False),
        sa.Column("cpu_usage", sa.Float(), nullable=False),
        sa.Column("incoming_bandwidth_speed", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("outgoing_bandwidth_speed", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("disk_total", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("disk_used", sa.BigInteger(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_system_stats_created_at", "system_stats", ["created_at"], unique=False)

    op.create_table(
        "observability_alert_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scope", sa.String(length=32), nullable=False),
        sa.Column("node_id", sa.Integer(), nullable=True),
        sa.Column("metric", sa.String(length=64), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("message", sa.String(length=512), nullable=False),
        sa.ForeignKeyConstraint(["node_id"], ["nodes.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_observability_alert_events_created_at",
        "observability_alert_events",
        ["created_at"],
        unique=False,
    )
    op.create_index("ix_node_stats_created_at", "node_stats", ["created_at"], unique=False)

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_node_stats_node_id_created_at ON node_stats (node_id, created_at DESC)"
        )
        try:
            op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")
            op.execute(
                "SELECT create_hypertable('system_stats', 'created_at', if_not_exists => TRUE, migrate_data => TRUE)"
            )
            op.execute(
                "SELECT create_hypertable('node_stats', 'created_at', if_not_exists => TRUE, migrate_data => TRUE)"
            )
        except Exception:
            pass


def downgrade() -> None:
    op.drop_index("ix_observability_alert_events_created_at", table_name="observability_alert_events")
    op.drop_table("observability_alert_events")
    op.drop_index("ix_system_stats_created_at", table_name="system_stats")
    op.drop_table("system_stats")
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP INDEX IF EXISTS ix_node_stats_node_id_created_at")
    op.drop_index("ix_node_stats_created_at", table_name="node_stats")
