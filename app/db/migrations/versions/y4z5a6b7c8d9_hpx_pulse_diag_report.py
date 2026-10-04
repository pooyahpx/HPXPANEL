"""Add hpx_pulses.diag_report for agent TCP/UDP path probes.

Revision ID: y4z5a6b7c8d9
Revises: x3y4z5a6b7c8
Create Date: 2026-10-04 12:00:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "y4z5a6b7c8d9"
down_revision = "x3y4z5a6b7c8"
branch_labels = None
depends_on = None

JSONB = sa.JSON().with_variant(postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    with op.batch_alter_table("hpx_pulses", schema=None) as batch_op:
        batch_op.add_column(sa.Column("diag_report", JSONB, nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("hpx_pulses", schema=None) as batch_op:
        batch_op.drop_column("diag_report")
