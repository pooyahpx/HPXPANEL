"""hpx tunnel iran agent join token fields

Revision ID: j1k2l3m4n5o6
Revises: i0j1k2l3m4n5
Create Date: 2026-08-26 03:55:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "j1k2l3m4n5o6"
down_revision = "i0j1k2l3m4n5"
branch_labels = None
depends_on = None

_STATUS_VALUES = (
    "running",
    "stopped",
    "starting",
    "stopping",
    "error",
    "unhealthy",
    "pending_claim",
)
_OLD_STATUS_VALUES = (
    "running",
    "stopped",
    "starting",
    "stopping",
    "error",
    "unhealthy",
)


def _mysql_status_enum(values: tuple[str, ...]) -> str:
    members = ", ".join(f"'{value}'" for value in values)
    return f"ALTER TABLE hpx_tunnels MODIFY COLUMN status ENUM({members}) NOT NULL DEFAULT 'stopped'"


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.execute("ALTER TYPE hpxtunnelstatus ADD VALUE IF NOT EXISTS 'pending_claim'")
    elif dialect in {"mysql", "mariadb"}:
        op.execute(_mysql_status_enum(_STATUS_VALUES))

    op.add_column("hpx_tunnels", sa.Column("join_token_hash", sa.String(length=128), nullable=True))
    op.add_column("hpx_tunnels", sa.Column("join_token_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("hpx_tunnels", sa.Column("agent_key_hash", sa.String(length=128), nullable=True))
    op.add_column("hpx_tunnels", sa.Column("agent_claimed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("hpx_tunnels", sa.Column("agent_last_seen", sa.DateTime(timezone=True), nullable=True))
    op.add_column("hpx_tunnels", sa.Column("agent_host", sa.String(length=255), nullable=True))
    op.add_column("hpx_tunnels", sa.Column("agent_command", sa.String(length=16), nullable=True))
    op.create_unique_constraint("uq_hpx_tunnels_join_token_hash", "hpx_tunnels", ["join_token_hash"])
    op.create_unique_constraint("uq_hpx_tunnels_agent_key_hash", "hpx_tunnels", ["agent_key_hash"])


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    op.drop_constraint("uq_hpx_tunnels_agent_key_hash", "hpx_tunnels", type_="unique")
    op.drop_constraint("uq_hpx_tunnels_join_token_hash", "hpx_tunnels", type_="unique")
    op.drop_column("hpx_tunnels", "agent_command")
    op.drop_column("hpx_tunnels", "agent_host")
    op.drop_column("hpx_tunnels", "agent_last_seen")
    op.drop_column("hpx_tunnels", "agent_claimed_at")
    op.drop_column("hpx_tunnels", "agent_key_hash")
    op.drop_column("hpx_tunnels", "join_token_expires_at")
    op.drop_column("hpx_tunnels", "join_token_hash")

    op.execute("UPDATE hpx_tunnels SET status = 'stopped' WHERE status = 'pending_claim'")

    if dialect == "postgresql":
        op.execute("ALTER TABLE hpx_tunnels ALTER COLUMN status DROP DEFAULT")
        op.execute("ALTER TYPE hpxtunnelstatus RENAME TO hpxtunnelstatus_old")
        op.execute(
            "CREATE TYPE hpxtunnelstatus AS ENUM "
            "('running', 'stopped', 'starting', 'stopping', 'error', 'unhealthy')"
        )
        op.execute(
            "ALTER TABLE hpx_tunnels ALTER COLUMN status TYPE hpxtunnelstatus "
            "USING status::text::hpxtunnelstatus"
        )
        op.execute("ALTER TABLE hpx_tunnels ALTER COLUMN status SET DEFAULT 'stopped'::hpxtunnelstatus")
        op.execute("DROP TYPE hpxtunnelstatus_old")
    elif dialect in {"mysql", "mariadb"}:
        op.execute(_mysql_status_enum(_OLD_STATUS_VALUES))
