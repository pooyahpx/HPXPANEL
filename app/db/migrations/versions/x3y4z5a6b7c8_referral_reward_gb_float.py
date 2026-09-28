"""referral reward data gb to float

Revision ID: x3y4z5a6b7c8
Revises: w2x3y4z5a6b7
Create Date: 2026-09-28 05:40:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "x3y4z5a6b7c8"
down_revision = "w2x3y4z5a6b7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("shop_configs") as batch_op:
        batch_op.alter_column(
            "referral_reward_data_gb",
            existing_type=sa.Integer(),
            type_=sa.Float(),
            existing_nullable=False,
            existing_server_default="0",
        )


def downgrade() -> None:
    with op.batch_alter_table("shop_configs") as batch_op:
        batch_op.alter_column(
            "referral_reward_data_gb",
            existing_type=sa.Float(),
            type_=sa.Integer(),
            existing_nullable=False,
            existing_server_default="0",
        )
