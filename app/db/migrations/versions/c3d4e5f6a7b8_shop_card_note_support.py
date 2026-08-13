"""shop card note, card photos

Revision ID: c3d4e5f6a7b8
Revises: a7b8c9d0e1f2
Create Date: 2026-08-13 15:30:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "c3d4e5f6a7b8"
down_revision = "a7b8c9d0e1f2"
branch_labels = None
depends_on = None

JSONB = sa.JSON().with_variant(postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    op.add_column("shop_configs", sa.Column("card_note", sa.String(length=1000), nullable=True))
    op.add_column("shop_configs", sa.Column("card_photos", JSONB, nullable=True))


def downgrade() -> None:
    op.drop_column("shop_configs", "card_photos")
    op.drop_column("shop_configs", "card_note")
