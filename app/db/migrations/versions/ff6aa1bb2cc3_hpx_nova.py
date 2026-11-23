"""hpx nova tunnels (isolated from pulse)

Revision ID: ff6aa1bb2cc3
Revises: ee5ff6aa1bb2
Create Date: 2026-11-23 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "ff6aa1bb2cc3"
down_revision = "ee5ff6aa1bb2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    dialect = op.get_bind().dialect.name
    bool_true = sa.text("true") if dialect == "postgresql" else sa.text("1")

    op.create_table(
        "hpx_novas",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=40), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending_claim",
                "running",
                "stopped",
                "starting",
                "stopping",
                "error",
                "unhealthy",
                "partial",
                name="hpxnovastatus",
            ),
            nullable=False,
            server_default="pending_claim",
        ),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=bool_true),
        sa.Column("engine", sa.String(length=32), nullable=False, server_default="nova"),
        sa.Column("carrier", sa.String(length=16), nullable=False, server_default="wss"),
        sa.Column("lanes", sa.Integer(), nullable=False, server_default="4"),
        sa.Column("resume", sa.Boolean(), nullable=False, server_default=bool_true),
        sa.Column("identity_encrypted", sa.Text(), nullable=False),
        sa.Column("iran_public_ip", sa.String(length=45), nullable=False),
        sa.Column("abroad_public_ip", sa.String(length=45), nullable=False),
        sa.Column("tunnel_port", sa.Integer(), nullable=False, server_default="8443"),
        sa.Column("sni", sa.String(length=255), nullable=True),
        sa.Column("ws_path", sa.String(length=128), nullable=True),
        sa.Column("port_forwards", sa.JSON(), nullable=True),
        sa.Column("proxy_listen", sa.String(length=64), nullable=True),
        sa.Column("note", sa.String(length=512), nullable=True),
        sa.Column("iran_join_token_hash", sa.String(length=128), nullable=True),
        sa.Column("iran_join_token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("abroad_join_token_hash", sa.String(length=128), nullable=True),
        sa.Column("abroad_join_token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("iran_agent_key_hash", sa.String(length=128), nullable=True),
        sa.Column("abroad_agent_key_hash", sa.String(length=128), nullable=True),
        sa.Column("iran_agent_claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("abroad_agent_claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("iran_agent_last_seen", sa.DateTime(timezone=True), nullable=True),
        sa.Column("abroad_agent_last_seen", sa.DateTime(timezone=True), nullable=True),
        sa.Column("iran_agent_host", sa.String(length=255), nullable=True),
        sa.Column("abroad_agent_host", sa.String(length=255), nullable=True),
        sa.Column("iran_agent_command", sa.String(length=64), nullable=True),
        sa.Column("abroad_agent_command", sa.String(length=64), nullable=True),
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.Column("message", sa.String(length=1024), nullable=True),
        sa.Column("last_status_change", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("iran_join_token_hash"),
        sa.UniqueConstraint("abroad_join_token_hash"),
        sa.UniqueConstraint("iran_agent_key_hash"),
        sa.UniqueConstraint("abroad_agent_key_hash"),
    )


def downgrade() -> None:
    op.drop_table("hpx_novas")
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        sa.Enum(name="hpxnovastatus").drop(bind, checkfirst=True)
