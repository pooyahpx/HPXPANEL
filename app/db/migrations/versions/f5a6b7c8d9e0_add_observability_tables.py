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
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
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
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scope", sa.String(length=32), nullable=False),
        sa.Column("node_id", sa.BigInteger(), nullable=True),
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
    op.create_index(
        "ix_node_stats_node_id_created_at",
        "node_stats",
        ["node_id", "created_at"],
        unique=False,
    )

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        timescale_available = bind.execute(
            sa.text("SELECT 1 FROM pg_available_extensions WHERE name = 'timescaledb' LIMIT 1")
        ).scalar()
        if timescale_available:
            with op.get_context().autocommit_block():
                op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")
                for table in ("system_stats", "node_stats"):
                    try:
                        op.execute(
                            sa.text(
                                f"SELECT create_hypertable('{table}', 'created_at', "
                                "if_not_exists => TRUE, migrate_data => TRUE)"
                            )
                        )
                    except Exception:
                        pass


def downgrade() -> None:
    op.drop_index("ix_observability_alert_events_created_at", table_name="observability_alert_events")
    op.drop_table("observability_alert_events")
    op.drop_index("ix_system_stats_created_at", table_name="system_stats")
    op.drop_table("system_stats")
    op.drop_index("ix_node_stats_node_id_created_at", table_name="node_stats")
    op.drop_index("ix_node_stats_created_at", table_name="node_stats")
