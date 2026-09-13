"""shop renewals + create-budget settle flags

Revision ID: p5q6r7s8t9u0
Revises: o4p5q6r7s8t9
Create Date: 2026-09-13 14:10:00.000000

"""

import sqlalchemy as sa
from alembic import op

from app.db.compiles_types import SqliteCompatibleBigInteger

revision = "p5q6r7s8t9u0"
down_revision = "o4p5q6r7s8t9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "shop_orders",
        sa.Column("order_kind", sa.String(length=16), nullable=False, server_default="purchase"),
    )

    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("shop_orders") as batch_op:
            batch_op.add_column(sa.Column("renew_user_id", SqliteCompatibleBigInteger(), nullable=True))
            batch_op.create_foreign_key(
                "fk_shop_orders_renew_user_id_users",
                "users",
                ["renew_user_id"],
                ["id"],
                ondelete="SET NULL",
            )
    else:
        op.add_column(
            "shop_orders",
            sa.Column(
                "renew_user_id",
                SqliteCompatibleBigInteger(),
                sa.ForeignKey("users.id", ondelete="SET NULL", name="fk_shop_orders_renew_user_id_users"),
                nullable=True,
            ),
        )

    op.add_column(
        "create_budget_ledger",
        sa.Column("settled_with_owner", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "create_budget_ledger",
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "create_budget_ledger",
        sa.Column("settled_by_admin_id", SqliteCompatibleBigInteger(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("create_budget_ledger", "settled_by_admin_id")
    op.drop_column("create_budget_ledger", "settled_at")
    op.drop_column("create_budget_ledger", "settled_with_owner")

    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("shop_orders") as batch_op:
            batch_op.drop_constraint("fk_shop_orders_renew_user_id_users", type_="foreignkey")
            batch_op.drop_column("renew_user_id")
    else:
        op.drop_constraint("fk_shop_orders_renew_user_id_users", "shop_orders", type_="foreignkey")
        op.drop_column("shop_orders", "renew_user_id")
    op.drop_column("shop_orders", "order_kind")
