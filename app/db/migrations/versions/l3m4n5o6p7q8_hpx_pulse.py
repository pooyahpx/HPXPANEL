"""hpx pulse tunnels

Revision ID: l3m4n5o6p7q8
Revises: k2l3m4n5o6p7
Create Date: 2026-08-27 02:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "l3m4n5o6p7q8"
down_revision = "k2l3m4n5o6p7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    dialect = op.get_bind().dialect.name
    bool_true = sa.text("true") if dialect == "postgresql" else sa.text("1")

    op.create_table(
        "hpx_pulses",
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
                name="hpxpulsestatus",
            ),
            nullable=False,
            server_default="pending_claim",
        ),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=bool_true),
        sa.Column("engine", sa.String(length=16), nullable=False, server_default="backpack"),
        sa.Column("profile_id", sa.String(length=64), nullable=False, server_default="pulse-stealth-balance"),
        sa.Column("goal", sa.String(length=16), nullable=False, server_default="balanced"),
        sa.Column("tunnel_mode", sa.String(length=32), nullable=False, server_default="direct_l3"),
        sa.Column("carrier", sa.String(length=16), nullable=True),
        sa.Column("preset", sa.String(length=16), nullable=False, server_default="balance"),
        sa.Column("token_encrypted", sa.String(length=512), nullable=False),
        sa.Column("iran_public_ip", sa.String(length=45), nullable=False),
        sa.Column("abroad_public_ip", sa.String(length=45), nullable=False),
        sa.Column("control_port", sa.Integer(), nullable=False, server_default="9067"),
        sa.Column("local_ip_iran", sa.String(length=45), nullable=False, server_default="10.10.0.1/30"),
        sa.Column("local_ip_abroad", sa.String(length=45), nullable=False, server_default="10.10.0.2/30"),
        sa.Column("port_forwards", sa.JSON(), nullable=True),
        sa.Column("domain", sa.String(length=255), nullable=True),
        sa.Column("sni_hint", sa.String(length=255), nullable=True),
        sa.Column("advice_json", sa.JSON(), nullable=True),
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
        sa.Column("iran_agent_command", sa.String(length=16), nullable=True),
        sa.Column("abroad_agent_command", sa.String(length=16), nullable=True),
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.Column("packet_loss_pct", sa.Float(), nullable=True),
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
    op.drop_table("hpx_pulses")
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        sa.Enum(name="hpxpulsestatus").drop(bind, checkfirst=True)
