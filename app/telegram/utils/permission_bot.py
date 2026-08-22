"""Bot helpers for owner-managed admin role permissions."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.models.admin_role import PermissionScope, RolePermissions

# (callback key, resource, action, enabled value)
PERM_TOGGLE_SPECS: dict[str, tuple[str, str, Any]] = {
    "nodes_reconnect": ("nodes", "reconnect", True),
    "nodes_update": ("nodes", "update", True),
    "settings_update": ("settings", "update", True),
    "admins_update": ("admins", "update", True),
    "users_delete_all": ("users", "delete", {"scope": PermissionScope.ALL}),
    "users_create_all": ("users", "create", True),
}

PERM_TOGGLE_ORDER = (
    "nodes_reconnect",
    "nodes_update",
    "settings_update",
    "admins_update",
    "users_delete_all",
    "users_create_all",
)


def permission_enabled(permissions: dict | None, resource: str, action: str) -> bool:
    if not permissions:
        return False
    resource_perms = permissions.get(resource) or {}
    value = resource_perms.get(action)
    if value is True:
        return True
    if isinstance(value, dict):
        scope = value.get("scope")
        if scope is None:
            return False
        try:
            return int(scope) >= int(PermissionScope.OWN)
        except (TypeError, ValueError):
            return False
    return False


def set_permission(permissions: dict | None, resource: str, action: str, enabled: bool, enabled_value: Any) -> dict:
    merged = deepcopy(permissions or {})
    resource_perms = dict(merged.get(resource) or {})
    resource_perms[action] = enabled_value if enabled else None
    merged[resource] = resource_perms
    return merged


def permissions_as_dict(permissions) -> dict:
    if permissions is None:
        return {}
    if isinstance(permissions, dict):
        return permissions
    return RolePermissions.model_validate(permissions).model_dump()


def toggle_permission(permissions: dict | None, toggle_key: str) -> dict:
    resource, action, enabled_value = PERM_TOGGLE_SPECS[toggle_key]
    enabled = not permission_enabled(permissions, resource, action)
    return set_permission(permissions, resource, action, enabled, enabled_value)


def permissions_from_role(role) -> RolePermissions:
    return RolePermissions.model_validate(role.permissions or {})
