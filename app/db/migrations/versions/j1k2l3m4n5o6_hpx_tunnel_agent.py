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

_old_status = sa.Enum(*_OLD_STATUS_VALUES, name="hpxtunnelstatus")
_new_status = sa.Enum(*_STATUS_VALUES, name="hpxtunnelstatus")


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
    elif dialect == "sqlite":
        # SQLite stores Enum as VARCHAR(len(longest)); pending_claim widens it.
        with op.batch_alter_table("hpx_tunnels", schema=None) as batch_op:
            batch_op.alter_column(
                "status",
                existing_type=_old_status,
                type_=_new_status,
                existing_nullable=False,
                existing_server_default="stopped",
            )

    # SQLite cannot ALTER constraints in-place — use batch mode for all dialects.
    with op.batch_alter_table("hpx_tunnels", schema=None) as batch_op:
        batch_op.add_column(sa.Column("join_token_hash", sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column("join_token_expires_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("agent_key_hash", sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column("agent_claimed_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("agent_last_seen", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("agent_host", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("agent_command", sa.String(length=16), nullable=True))
        batch_op.create_unique_constraint("uq_hpx_tunnels_join_token_hash", ["join_token_hash"])
        batch_op.create_unique_constraint("uq_hpx_tunnels_agent_key_hash", ["agent_key_hash"])


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    with op.batch_alter_table("hpx_tunnels", schema=None) as batch_op:
        batch_op.drop_constraint("uq_hpx_tunnels_agent_key_hash", type_="unique")
        batch_op.drop_constraint("uq_hpx_tunnels_join_token_hash", type_="unique")
        batch_op.drop_column("agent_command")
        batch_op.drop_column("agent_host")
        batch_op.drop_column("agent_last_seen")
        batch_op.drop_column("agent_claimed_at")
        batch_op.drop_column("agent_key_hash")
        batch_op.drop_column("join_token_expires_at")
        batch_op.drop_column("join_token_hash")

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
    elif dialect == "sqlite":
        with op.batch_alter_table("hpx_tunnels", schema=None) as batch_op:
            batch_op.alter_column(
                "status",
                existing_type=_new_status,
                type_=_old_status,
                existing_nullable=False,
                existing_server_default="stopped",
            )
