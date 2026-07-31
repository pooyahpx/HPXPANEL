"""add IKEv2 and L2TP backend support

Revision ID: d3a8f6c1e4b2
Revises: fb32155473c1
Create Date: 2026-07-30 06:20:00.000000

"""

import json
import secrets

import sqlalchemy as sa
from alembic import op

revision = "d3a8f6c1e4b2"
down_revision = "fb32155473c1"
branch_labels = None
depends_on = None

_OLD_CORE_TYPES = ("xray", "wg", "mtproto", "singbox")
_NEW_CORE_TYPES = ("xray", "wg", "ikev2", "l2tp", "mtproto", "singbox")


def _mysql_core_enum(values: tuple[str, ...]) -> str:
    members = ", ".join(f"'{value}'" for value in values)
    return f"ALTER TABLE core_configs MODIFY COLUMN type ENUM({members}) NOT NULL DEFAULT 'xray'"


def _upgrade_core_type(bind) -> None:
    dialect = bind.dialect.name
    if dialect == "postgresql":
        op.execute("ALTER TYPE coretype ADD VALUE IF NOT EXISTS 'ikev2'")
        op.execute("ALTER TYPE coretype ADD VALUE IF NOT EXISTS 'l2tp'")
    elif dialect in {"mysql", "mariadb"}:
        op.execute(_mysql_core_enum(_NEW_CORE_TYPES))


def _downgrade_core_type(bind) -> None:
    dialect = bind.dialect.name
    op.execute("UPDATE core_configs SET type = 'xray' WHERE type IN ('ikev2', 'l2tp')")

    if dialect == "postgresql":
        op.execute("ALTER TABLE core_configs ALTER COLUMN type DROP DEFAULT")
        op.execute("ALTER TYPE coretype RENAME TO coretype_with_ipsec")
        op.execute("CREATE TYPE coretype AS ENUM ('xray', 'wg', 'mtproto', 'singbox')")
        op.execute(
            "ALTER TABLE core_configs ALTER COLUMN type TYPE coretype "
            "USING type::text::coretype"
        )
        op.execute("ALTER TABLE core_configs ALTER COLUMN type SET DEFAULT 'xray'::coretype")
        op.execute("DROP TYPE coretype_with_ipsec")
    elif dialect in {"mysql", "mariadb"}:
        op.execute(_mysql_core_enum(_OLD_CORE_TYPES))


def _load_settings(value) -> dict | None:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (TypeError, ValueError):
            return None
    if value is None:
        return {}
    return dict(value) if isinstance(value, dict) else None


def _migrate_proxy_settings(bind, *, remove: bool = False) -> None:
    users = sa.table(
        "users",
        sa.column("id", sa.BigInteger),
        sa.column("proxy_settings", sa.JSON),
    )
    rows = bind.execute(sa.select(users.c.id, users.c.proxy_settings)).fetchall()
    updates = []

    for user_id, raw_settings in rows:
        settings = _load_settings(raw_settings)
        if settings is None:
            continue
        changed = False

        if remove:
            changed = settings.pop("ikev2", None) is not None
        else:
            ikev2 = settings.get("ikev2")
            if not isinstance(ikev2, dict):
                ikev2 = {}
            if not ikev2.get("username"):
                ikev2["username"] = str(user_id)
                changed = True
            if not ikev2.get("password"):
                ikev2["password"] = secrets.token_urlsafe(24)
                changed = True
            if settings.get("ikev2") != ikev2:
                changed = True
            settings["ikev2"] = ikev2

        if changed:
            updates.append({"_id": user_id, "proxy_settings": settings})

    if updates:
        bind.execute(
            users.update().where(users.c.id == sa.bindparam("_id")),
            updates,
        )


def upgrade() -> None:
    bind = op.get_bind()
    _upgrade_core_type(bind)
    _migrate_proxy_settings(bind)


def downgrade() -> None:
    bind = op.get_bind()
    _migrate_proxy_settings(bind, remove=True)
    _downgrade_core_type(bind)
