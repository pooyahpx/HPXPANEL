"""add append-only audit logs

Revision ID: i8j9k0l1m2n3
Revises: h7i8j9k0l1m2
Create Date: 2026-09-04 03:10:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

from app.db.compiles_types import SqliteCompatibleBigInteger

revision = "i8j9k0l1m2n3"
down_revision = "h7i8j9k0l1m2"
branch_labels = None
depends_on = None

json_type = sa.JSON().with_variant(JSONB(none_as_null=True), "postgresql")


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", SqliteCompatibleBigInteger(), autoincrement=True, nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("resource", sa.String(length=64), nullable=False),
        sa.Column("result", sa.String(length=16), nullable=False),
        sa.Column("actor_id", sa.BigInteger(), nullable=True),
        sa.Column("actor_username", sa.String(length=128), nullable=True),
        sa.Column("source_ip", sa.String(length=64), nullable=True),
        sa.Column("resource_id", sa.String(length=256), nullable=True),
        sa.Column("before", json_type, nullable=True),
        sa.Column("after", json_type, nullable=True),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("result IN ('success', 'failure')", name=op.f("ck_audit_logs_result")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_logs")),
    )
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"], unique=False)
    op.create_index("ix_audit_logs_actor_id", "audit_logs", ["actor_id"], unique=False)
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"], unique=False)
    op.create_index("ix_audit_logs_resource", "audit_logs", ["resource"], unique=False)
    op.create_index("ix_audit_logs_result", "audit_logs", ["result"], unique=False)
    op.create_index("ix_audit_logs_actor_action", "audit_logs", ["actor_id", "action"], unique=False)
    op.create_index("ix_audit_logs_resource_result", "audit_logs", ["resource", "result"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_audit_logs_resource_result", table_name="audit_logs")
    op.drop_index("ix_audit_logs_actor_action", table_name="audit_logs")
    op.drop_index("ix_audit_logs_result", table_name="audit_logs")
    op.drop_index("ix_audit_logs_resource", table_name="audit_logs")
    op.drop_index("ix_audit_logs_action", table_name="audit_logs")
    op.drop_index("ix_audit_logs_actor_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
    op.drop_table("audit_logs")
