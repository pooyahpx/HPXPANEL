"""Widen nodes.xray_version / nodes.node_version for multi-core nodes.

A node running several cores reports one version per core, e.g.
"v1.0.20210914, v1.0.20210914, 26.3.27", which overflowed VARCHAR(32) and
made the panel fail at startup while saving node status.

Revision ID: bb2cc3dd4ee5
Revises: aa1bb2cc3dd4
Create Date: 2026-10-14 09:40:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "bb2cc3dd4ee5"
down_revision = "aa1bb2cc3dd4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("nodes", schema=None) as batch_op:
        batch_op.alter_column(
            "xray_version",
            existing_type=sa.String(length=32),
            type_=sa.String(length=128),
            existing_nullable=True,
        )
        batch_op.alter_column(
            "node_version",
            existing_type=sa.String(length=32),
            type_=sa.String(length=128),
            existing_nullable=True,
        )


def downgrade() -> None:
    # Trim first so the narrower type can be applied to existing rows.
    op.execute("UPDATE nodes SET xray_version = SUBSTR(xray_version, 1, 32) WHERE LENGTH(xray_version) > 32")
    op.execute("UPDATE nodes SET node_version = SUBSTR(node_version, 1, 32) WHERE LENGTH(node_version) > 32")
    with op.batch_alter_table("nodes", schema=None) as batch_op:
        batch_op.alter_column(
            "xray_version",
            existing_type=sa.String(length=128),
            type_=sa.String(length=32),
            existing_nullable=True,
        )
        batch_op.alter_column(
            "node_version",
            existing_type=sa.String(length=128),
            type_=sa.String(length=32),
            existing_nullable=True,
        )
