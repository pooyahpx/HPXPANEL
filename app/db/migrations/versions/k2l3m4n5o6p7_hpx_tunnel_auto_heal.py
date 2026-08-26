"""hpx tunnel auto-heal fields

Revision ID: k2l3m4n5o6p7
Revises: j1k2l3m4n5o6
Create Date: 2026-08-26 08:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "k2l3m4n5o6p7"
down_revision = "j1k2l3m4n5o6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Postgres rejects INTEGER defaults on BOOLEAN (DEFAULT 1).
    dialect = op.get_bind().dialect.name
    bool_true = sa.text("true") if dialect == "postgresql" else sa.text("1")

    with op.batch_alter_table("hpx_tunnels", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "auto_heal_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=bool_true,
            )
        )
        batch_op.add_column(sa.Column("last_heal_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("last_heal_action", sa.String(length=256), nullable=True))
        batch_op.add_column(
            sa.Column(
                "heal_count_window",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("0"),
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("hpx_tunnels", schema=None) as batch_op:
        batch_op.drop_column("heal_count_window")
        batch_op.drop_column("last_heal_action")
        batch_op.drop_column("last_heal_at")
        batch_op.drop_column("auto_heal_enabled")
