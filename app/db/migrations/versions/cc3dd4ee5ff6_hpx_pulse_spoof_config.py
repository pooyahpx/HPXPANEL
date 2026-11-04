"""Add hpx_pulses.spoof_config for Direct Spoof carrier settings.

Revision ID: cc3dd4ee5ff6
Revises: bb2cc3dd4ee5
Create Date: 2026-11-04 18:10:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "cc3dd4ee5ff6"
down_revision = "bb2cc3dd4ee5"
branch_labels = None
depends_on = None

JSONB = sa.JSON().with_variant(postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    with op.batch_alter_table("hpx_pulses", schema=None) as batch_op:
        batch_op.add_column(sa.Column("spoof_config", JSONB, nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("hpx_pulses", schema=None) as batch_op:
        batch_op.drop_column("spoof_config")
