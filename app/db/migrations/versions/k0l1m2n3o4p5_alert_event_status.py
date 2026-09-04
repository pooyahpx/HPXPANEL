"""add alert event status workflow fields

Revision ID: k0l1m2n3o4p5
Revises: j9k0l1m2n3o4
Create Date: 2026-09-04 13:50:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "k0l1m2n3o4p5"
down_revision = "j9k0l1m2n3o4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "observability_alert_events",
        sa.Column("status", sa.String(length=16), nullable=False, server_default="open"),
    )
    op.add_column(
        "observability_alert_events",
        sa.Column("acked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "observability_alert_events",
        sa.Column("acked_by", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "observability_alert_events",
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "observability_alert_events",
        sa.Column("resolved_by", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "observability_alert_events",
        sa.Column("note", sa.String(length=500), nullable=True),
    )
    op.create_index(
        "ix_observability_alert_events_status",
        "observability_alert_events",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_observability_alert_events_status", table_name="observability_alert_events")
    op.drop_column("observability_alert_events", "note")
    op.drop_column("observability_alert_events", "resolved_by")
    op.drop_column("observability_alert_events", "resolved_at")
    op.drop_column("observability_alert_events", "acked_by")
    op.drop_column("observability_alert_events", "acked_at")
    op.drop_column("observability_alert_events", "status")
