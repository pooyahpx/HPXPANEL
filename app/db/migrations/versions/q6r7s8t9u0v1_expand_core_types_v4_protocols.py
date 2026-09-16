"""expand core types for panel protocol backends

Revision ID: q6r7s8t9u0v1
Revises: p5q6r7s8t9u0
Create Date: 2026-09-16 14:30:00.000000

"""

from alembic import op

revision = "q6r7s8t9u0v1"
down_revision = "p5q6r7s8t9u0"
branch_labels = None
depends_on = None

_OLD_CORE_TYPES = ("xray", "wg", "ikev2", "l2tp", "openvpn", "mtproto", "singbox")
_NEW_CORE_TYPES = (
    "xray",
    "wg",
    "ikev2",
    "l2tp",
    "openvpn",
    "pptp",
    "openconnect",
    "sstp",
    "wg_c",
    "amneziawg",
    "gre",
    "ssh",
    "mtproto",
    "singbox",
)
_NEW_VALUES = ("pptp", "openconnect", "sstp", "wg_c", "amneziawg", "gre", "ssh")


def _mysql_core_enum(values: tuple[str, ...]) -> str:
    members = ", ".join(f"'{value}'" for value in values)
    return f"ALTER TABLE core_configs MODIFY COLUMN type ENUM({members}) NOT NULL DEFAULT 'xray'"


def _upgrade_core_type(bind) -> None:
    dialect = bind.dialect.name
    if dialect == "postgresql":
        for value in _NEW_VALUES:
            op.execute(f"ALTER TYPE coretype ADD VALUE IF NOT EXISTS '{value}'")
    elif dialect in {"mysql", "mariadb"}:
        op.execute(_mysql_core_enum(_NEW_CORE_TYPES))


def _downgrade_core_type(bind) -> None:
    dialect = bind.dialect.name
    for value in _NEW_VALUES:
        op.execute(f"UPDATE core_configs SET type = 'xray' WHERE type = '{value}'")

    if dialect == "postgresql":
        old_members = ", ".join(f"'{value}'" for value in _OLD_CORE_TYPES)
        op.execute("ALTER TABLE core_configs ALTER COLUMN type DROP DEFAULT")
        op.execute("ALTER TYPE coretype RENAME TO coretype_with_v4_protocols")
        op.execute(f"CREATE TYPE coretype AS ENUM ({old_members})")
        op.execute(
            "ALTER TABLE core_configs ALTER COLUMN type TYPE coretype "
            "USING type::text::coretype"
        )
        op.execute("ALTER TABLE core_configs ALTER COLUMN type SET DEFAULT 'xray'::coretype")
        op.execute("DROP TYPE coretype_with_v4_protocols")
    elif dialect in {"mysql", "mariadb"}:
        op.execute(_mysql_core_enum(_OLD_CORE_TYPES))


def upgrade() -> None:
    bind = op.get_bind()
    _upgrade_core_type(bind)


def downgrade() -> None:
    bind = op.get_bind()
    _downgrade_core_type(bind)
