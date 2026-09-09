"""incident timeline/SOAR fields and admin WebAuthn credentials

Revision ID: n3o4p5q6r7s8
Revises: m2n3o4p5q6r7
Create Date: 2026-09-09 13:20:00.000000

"""

import sqlalchemy as sa
from alembic import op

from app.db.compiles_types import SqliteCompatibleBigInteger

revision = "n3o4p5q6r7s8"
down_revision = "m2n3o4p5q6r7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "observability_alert_events",
        sa.Column("severity", sa.String(length=16), nullable=False, server_default="warning"),
    )
    op.add_column(
        "observability_alert_events",
        sa.Column("assignee", sa.String(length=64), nullable=True),
    )

    op.create_table(
        "observability_alert_timeline_events",
        sa.Column("id", SqliteCompatibleBigInteger(), autoincrement=True, nullable=False),
        sa.Column("alert_id", SqliteCompatibleBigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor", sa.String(length=64), nullable=True),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("from_status", sa.String(length=16), nullable=True),
        sa.Column("to_status", sa.String(length=16), nullable=True),
        sa.Column("message", sa.String(length=1000), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["alert_id"], ["observability_alert_events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_observability_alert_timeline_events")),
    )
    op.create_index(
        "ix_observability_alert_timeline_events_alert_id",
        "observability_alert_timeline_events",
        ["alert_id"],
        unique=False,
    )
    op.create_index(
        "ix_observability_alert_timeline_events_created_at",
        "observability_alert_timeline_events",
        ["created_at"],
        unique=False,
    )

    op.create_table(
        "admin_webauthn_credentials",
        sa.Column("id", SqliteCompatibleBigInteger(), autoincrement=True, nullable=False),
        sa.Column("admin_id", SqliteCompatibleBigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("credential_id", sa.String(length=512), nullable=False),
        sa.Column("public_key", sa.Text(), nullable=False),
        sa.Column("sign_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("transports", sa.JSON(), nullable=True),
        sa.Column("aaguid", sa.String(length=64), nullable=True),
        sa.Column("nickname", sa.String(length=128), nullable=False, server_default="Security key"),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["admin_id"], ["admins.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_admin_webauthn_credentials")),
        sa.UniqueConstraint("credential_id", name="uq_admin_webauthn_credentials_credential_id"),
    )
    op.create_index(
        "ix_admin_webauthn_credentials_admin_id",
        "admin_webauthn_credentials",
        ["admin_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_admin_webauthn_credentials_admin_id", table_name="admin_webauthn_credentials")
    op.drop_table("admin_webauthn_credentials")
    op.drop_index("ix_observability_alert_timeline_events_created_at", table_name="observability_alert_timeline_events")
    op.drop_index("ix_observability_alert_timeline_events_alert_id", table_name="observability_alert_timeline_events")
    op.drop_table("observability_alert_timeline_events")
    op.drop_column("observability_alert_events", "assignee")
    op.drop_column("observability_alert_events", "severity")
