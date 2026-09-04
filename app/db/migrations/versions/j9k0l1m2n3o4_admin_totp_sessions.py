"""add admin totp and sessions

Revision ID: j9k0l1m2n3o4
Revises: i8j9k0l1m2n3
Create Date: 2026-09-04 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

from app.db.compiles_types import SqliteCompatibleBigInteger

revision = "j9k0l1m2n3o4"
down_revision = "i8j9k0l1m2n3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Encrypted TOTP secrets need more than 64 chars (Fernet ciphertext).
    op.add_column("admins", sa.Column("totp_secret", sa.String(length=512), nullable=True))
    op.add_column(
        "admins",
        sa.Column("totp_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.create_table(
        "admin_sessions",
        sa.Column("id", SqliteCompatibleBigInteger(), autoincrement=True, nullable=False),
        sa.Column("admin_id", sa.BigInteger(), nullable=False),
        sa.Column("jti", sa.String(length=64), nullable=False),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("ip", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["admin_id"], ["admins.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_admin_sessions")),
    )
    op.create_index("ix_admin_sessions_jti", "admin_sessions", ["jti"], unique=True)
    op.create_index("ix_admin_sessions_admin_id", "admin_sessions", ["admin_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_admin_sessions_admin_id", table_name="admin_sessions")
    op.drop_index("ix_admin_sessions_jti", table_name="admin_sessions")
    op.drop_table("admin_sessions")
    op.drop_column("admins", "totp_enabled")
    op.drop_column("admins", "totp_secret")
