"""add admin access_overrides for per-admin group/template restrictions

Revision ID: f1a2b3c4d5e6
Revises: e4b7c2d9f1a3
Create Date: 2026-08-12 18:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "f1a2b3c4d5e6"
down_revision = "e4b7c2d9f1a3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "admins",
        sa.Column(
            "access_overrides",
            sa.JSON().with_variant(postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), "postgresql"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("admins", "access_overrides")
