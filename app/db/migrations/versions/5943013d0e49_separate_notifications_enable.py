"""separate notifications enable

Revision ID: 5943013d0e49
Revises: 8350e561677a
Create Date: 2025-10-30 15:05:05.388432

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
import json


# revision identifiers, used by Alembic.
revision = '5943013d0e49'
down_revision = '8350e561677a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Transform old boolean notification_enable fields to nested granular objects.
    Old structure: {"admin": true, "user": false, "login": true, ...}
    New structure: {"admin": {"create": true, "modify": true, ...}, ...}
    """
    connection = op.get_bind()

    # Get all settings rows
    result = connection.execute(text("SELECT id, notification_enable FROM settings"))
    rows = result.fetchall()

    for row in rows:
        settings_id = row[0]
        old_enable_json = row[1]

        # Parse the old JSON structure
        if not old_enable_json:
            continue

        # Handle JSON parsing for different database types
        if isinstance(old_enable_json, str):
            old_enable = json.loads(old_enable_json)
        else:
            old_enable = old_enable_json

        # Extract old values once
        admin_val = old_enable.get("admin", True)
        core_val = old_enable.get("core", True)
        group_val = old_enable.get("group", True)
        host_val = old_enable.get("host", True)
        login_val = old_enable.get("login", True)
        node_val = old_enable.get("node", True)
        user_val = old_enable.get("user", True)
        user_template_val = old_enable.get("user_template", True)
        days_left_val = old_enable.get("days_left", True)
        percentage_reached_val = old_enable.get("percentage_reached", True)

        # Create new granular structure
        new_enable = {
            "admin": {
                "create": admin_val,
                "modify": admin_val,
                "delete": admin_val,
                "reset_usage": admin_val,
                "login": login_val,
            },
            "core": {
                "create": core_val,
                "modify": core_val,
                "delete": core_val,
            },
            "group": {
                "create": group_val,
                "modify": group_val,
                "delete": group_val,
            },
            "host": {
                "create": host_val,
                "modify": host_val,
                "delete": host_val,
                "modify_hosts": host_val,
            },
            "node": {
                "create": node_val,
                "modify": node_val,
                "delete": node_val,
                "connect": node_val,
                "error": node_val,
            },
            "user": {
                "create": user_val,
                "modify": user_val,
                "delete": user_val,
                "status_change": user_val,
                "reset_data_usage": user_val,
                "data_reset_by_next": user_val,
                "subscription_revoked": user_val,
            },
            "user_template": {
                "create": user_template_val,
                "modify": user_template_val,
                "delete": user_template_val,
            },
            "days_left": days_left_val,
            "percentage_reached": percentage_reached_val,
        }

        # Update the row with new structure
        connection.execute(
            text("UPDATE settings SET notification_enable = :new_enable WHERE id = :settings_id"),
            {"new_enable": json.dumps(new_enable), "settings_id": settings_id}
        )


def downgrade() -> None:
    """
    Rollback: Convert nested objects back to simple booleans.
    New structure: {"admin": {"create": true, ...}, ...}
    Old structure: {"admin": true, "user": false, ...}
    """
    connection = op.get_bind()

    # Get all settings rows
    result = connection.execute(text("SELECT id, notification_enable FROM settings"))
    rows = result.fetchall()

    for row in rows:
        settings_id = row[0]
        new_enable_json = row[1]

        if not new_enable_json:
            continue

        # Handle JSON parsing for different database types
        if isinstance(new_enable_json, str):
            new_enable = json.loads(new_enable_json)
        else:
            new_enable = new_enable_json

        # Check if any sub-field is enabled for each entity
        def any_enabled(obj):
            if isinstance(obj, dict):
                return any(obj.values())
            return obj

        # Extract new values once
        admin_obj = new_enable.get("admin", {})
        core_obj = new_enable.get("core", {})
        group_obj = new_enable.get("group", {})
        host_obj = new_enable.get("host", {})
        node_obj = new_enable.get("node", {})
        user_obj = new_enable.get("user", {})
        user_template_obj = new_enable.get("user_template", {})

        # Create old boolean structure
        old_enable = {
            "admin": any_enabled(admin_obj),
            "core": any_enabled(core_obj),
            "group": any_enabled(group_obj),
            "host": any_enabled(host_obj),
            "login": admin_obj.get("login", True) if isinstance(admin_obj, dict) else True,
            "node": any_enabled(node_obj),
            "user": any_enabled(user_obj),
            "user_template": any_enabled(user_template_obj),
            "days_left": new_enable.get("days_left", True),
            "percentage_reached": new_enable.get("percentage_reached", True),
        }

        # Update the row with old structure
        connection.execute(
            text("UPDATE settings SET notification_enable = :old_enable WHERE id = :settings_id"),
            {"old_enable": json.dumps(old_enable), "settings_id": settings_id}
        )
