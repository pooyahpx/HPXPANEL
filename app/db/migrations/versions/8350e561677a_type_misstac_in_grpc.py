"""type misstac in gRPC

Revision ID: 8350e561677a
Revises: 084b8004104c
Create Date: 2025-10-28 10:46:31.276627

"""
import json

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = '8350e561677a'
down_revision = '084b8004104c'
branch_labels = None
depends_on = None


def _load_transport_settings(raw):
    if raw is None:
        return 

    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8")

    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return

    if isinstance(raw, dict):
        return dict(raw)



def _persist_updates(connection, updates):
    if not updates:
        return

    update_stmt = sa.text("UPDATE hosts SET transport_settings = :settings WHERE id = :host_id")
    for host_id, settings in updates:
        connection.execute(
            update_stmt,
            {"settings": json.dumps(settings), "host_id": host_id},
        )


def upgrade() -> None:
    connection = op.get_bind()
    rows = connection.execute(sa.text("SELECT id, transport_settings FROM hosts")).mappings().all()

    if not rows:
        return

    updates = []

    for row in rows:
        transport_settings = _load_transport_settings(row.get("transport_settings"))
        if transport_settings is None:
            continue

        grpc_settings = transport_settings.get("grpc_settings")
        if not isinstance(grpc_settings, dict):
            continue

        if "permit_without_stream" not in grpc_settings:
            continue

        current_value = grpc_settings.get("permit_without_stream")
        if isinstance(current_value, bool) and current_value is False:
            continue

        grpc_settings["permit_without_stream"] = False
        updates.append((row["id"], transport_settings))

    _persist_updates(connection, updates)


def downgrade() -> None:
    connection = op.get_bind()
    rows = connection.execute(sa.text("SELECT id, transport_settings FROM hosts")).mappings().all()

    if not rows:
        return

    updates = []

    for row in rows:
        transport_settings = _load_transport_settings(row.get("transport_settings"))
        if transport_settings is None:
            continue

        grpc_settings = transport_settings.get("grpc_settings")
        if not isinstance(grpc_settings, dict):
            continue

        if "permit_without_stream" not in grpc_settings:
            continue

        current_value = grpc_settings.get("permit_without_stream")
        if isinstance(current_value, bool):
            grpc_settings["permit_without_stream"] = int(current_value)
        elif isinstance(current_value, int):
            continue
        else:
            grpc_settings["permit_without_stream"] = 0

        updates.append((row["id"], transport_settings))

    _persist_updates(connection, updates)
