"""add OpenVPN backend support

Revision ID: e4f5a6b7c8d9
Revises: l3m4n5o6p7q8
Create Date: 2026-09-01 23:30:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "e4f5a6b7c8d9"
down_revision = "l3m4n5o6p7q8"
branch_labels = None
depends_on = None

_OLD_CORE_TYPES = ("xray", "wg", "ikev2", "l2tp", "mtproto", "singbox")
_NEW_CORE_TYPES = ("xray", "wg", "ikev2", "l2tp", "openvpn", "mtproto", "singbox")


def _mysql_core_enum(values: tuple[str, ...]) -> str:
    members = ", ".join(f"'{value}'" for value in values)
    return f"ALTER TABLE core_configs MODIFY COLUMN type ENUM({members}) NOT NULL DEFAULT 'xray'"


def _upgrade_core_type(bind) -> None:
    dialect = bind.dialect.name
    if dialect == "postgresql":
        op.execute("ALTER TYPE coretype ADD VALUE IF NOT EXISTS 'openvpn'")
    elif dialect in {"mysql", "mariadb"}:
        op.execute(_mysql_core_enum(_NEW_CORE_TYPES))


def _downgrade_core_type(bind) -> None:
    dialect = bind.dialect.name
    op.execute("UPDATE core_configs SET type = 'xray' WHERE type = 'openvpn'")

    if dialect == "postgresql":
        op.execute("ALTER TABLE core_configs ALTER COLUMN type DROP DEFAULT")
        op.execute("ALTER TYPE coretype RENAME TO coretype_with_openvpn")
        op.execute("CREATE TYPE coretype AS ENUM ('xray', 'wg', 'ikev2', 'l2tp', 'mtproto', 'singbox')")
        op.execute(
            "ALTER TABLE core_configs ALTER COLUMN type TYPE coretype "
            "USING type::text::coretype"
        )
        op.execute("ALTER TABLE core_configs ALTER COLUMN type SET DEFAULT 'xray'::coretype")
        op.execute("DROP TYPE coretype_with_openvpn")
    elif dialect in {"mysql", "mariadb"}:
        op.execute(_mysql_core_enum(_OLD_CORE_TYPES))


def upgrade() -> None:
    bind = op.get_bind()
    _upgrade_core_type(bind)


def downgrade() -> None:
    bind = op.get_bind()
    _downgrade_core_type(bind)
