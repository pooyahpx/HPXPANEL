"""shop payment hardening: FX rate, awaiting_payment/expired, unpaid TTL

Revision ID: u0v1w2x3y4z5
Revises: t9u0v1w2x3y4
Create Date: 2026-09-19 03:10:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "u0v1w2x3y4z5"
down_revision = "t9u0v1w2x3y4"
branch_labels = None
depends_on = None

OLD_STATUSES = ("pending", "approved", "rejected")
NEW_STATUSES = ("pending", "approved", "rejected", "awaiting_payment", "expired")


def _upgrade_enum(bind) -> None:
    dialect = bind.dialect.name
    if dialect == "postgresql":
        # ADD VALUE cannot run inside a transaction block on some PG versions;
        # use DO block with exception handling for idempotency.
        for value in ("awaiting_payment", "expired"):
            op.execute(
                sa.text(
                    f"""
                    DO $$ BEGIN
                        ALTER TYPE shoporderstatus ADD VALUE '{value}';
                    EXCEPTION
                        WHEN duplicate_object THEN null;
                    END $$;
                    """
                )
            )
        return

    if dialect in ("mysql", "mariadb"):
        op.execute(
            "ALTER TABLE shop_orders MODIFY COLUMN status "
            "ENUM('pending','approved','rejected','awaiting_payment','expired') "
            "NOT NULL DEFAULT 'pending'"
        )
        return

    # SQLite / others: recreate via batch alter
    old_type = sa.Enum(*OLD_STATUSES, name="shoporderstatus")
    new_type = sa.Enum(*NEW_STATUSES, name="shoporderstatus")
    with op.batch_alter_table("shop_orders") as batch_op:
        batch_op.alter_column(
            "status",
            existing_type=old_type,
            type_=new_type,
            existing_nullable=False,
            server_default="pending",
        )


def _downgrade_enum(bind) -> None:
    dialect = bind.dialect.name
    if dialect == "postgresql":
        # Map new values back, then rebuild enum (PG cannot drop enum values easily).
        op.execute(
            sa.text(
                "UPDATE shop_orders SET status = 'rejected' "
                "WHERE status::text IN ('awaiting_payment', 'expired')"
            )
        )
        op.execute(sa.text("ALTER TYPE shoporderstatus RENAME TO shoporderstatus_old"))
        postgresql.ENUM(*OLD_STATUSES, name="shoporderstatus").create(bind, checkfirst=False)
        op.execute(
            sa.text(
                "ALTER TABLE shop_orders ALTER COLUMN status TYPE shoporderstatus "
                "USING status::text::shoporderstatus"
            )
        )
        op.execute(sa.text("DROP TYPE shoporderstatus_old"))
        return

    if dialect in ("mysql", "mariadb"):
        op.execute(
            "UPDATE shop_orders SET status = 'rejected' "
            "WHERE status IN ('awaiting_payment', 'expired')"
        )
        op.execute(
            "ALTER TABLE shop_orders MODIFY COLUMN status "
            "ENUM('pending','approved','rejected') NOT NULL DEFAULT 'pending'"
        )
        return

    old_type = sa.Enum(*OLD_STATUSES, name="shoporderstatus")
    new_type = sa.Enum(*NEW_STATUSES, name="shoporderstatus")
    with op.batch_alter_table("shop_orders") as batch_op:
        batch_op.alter_column(
            "status",
            existing_type=new_type,
            type_=old_type,
            existing_nullable=False,
            server_default="pending",
        )


def upgrade() -> None:
    op.add_column(
        "shop_configs",
        sa.Column("pay_fx_toman_per_usd", sa.BigInteger(), nullable=False, server_default="600000"),
    )
    op.add_column(
        "shop_configs",
        sa.Column("pay_unpaid_expire_minutes", sa.Integer(), nullable=False, server_default="60"),
    )
    _upgrade_enum(op.get_bind())


def downgrade() -> None:
    _downgrade_enum(op.get_bind())
    op.drop_column("shop_configs", "pay_unpaid_expire_minutes")
    op.drop_column("shop_configs", "pay_fx_toman_per_usd")
