"""Unit tests for app/operation/permissions.py"""

import pytest

from app.models.admin import AdminDetails
from app.operation.permissions import (
    PermissionDenied,
    enforce_permission,
    enforce_scope,
    get_allowed_group_ids,
    get_effective_limits,
)


def _make_admin(*, is_owner=False, permissions=None, limits=None, overrides=None, access=None, access_overrides=None, admin_id=10):
    role = {
        "is_owner": is_owner,
        "permissions": permissions or {},
        "limits": limits or {},
        "features": {},
        "access": access or {},
    }
    return AdminDetails(
        id=admin_id,
        username="testadmin",
        role=role,
        permission_overrides=overrides,
        access_overrides=access_overrides,
    )


# Scope constants for tests
SCOPE_OWN = {"scope": 1}
SCOPE_ALL = {"scope": 2}
SCOPE_NONE = {"scope": 0}


# --- enforce_permission ---


def test_owner_bypasses_all_checks():
    admin = _make_admin(is_owner=True)
    enforce_permission(admin, "users", "delete")  # should not raise


def test_allowed_action_passes():
    admin = _make_admin(permissions={"users": {"read": True}})
    enforce_permission(admin, "users", "read")  # should not raise


def test_missing_resource_raises():
    admin = _make_admin(permissions={})
    with pytest.raises(PermissionDenied):
        enforce_permission(admin, "users", "read")


def test_missing_action_raises():
    admin = _make_admin(permissions={"users": {"read": True}})
    with pytest.raises(PermissionDenied):
        enforce_permission(admin, "users", "delete")


def test_scope_own_is_allowed_at_permission_level():
    admin = _make_admin(permissions={"users": {"read": SCOPE_OWN}})
    enforce_permission(admin, "users", "read")  # should not raise (scope checked separately)


def test_scope_all_is_allowed():
    admin = _make_admin(permissions={"users": {"read": SCOPE_ALL}})
    enforce_permission(admin, "users", "read")  # should not raise


def test_scope_none_raises():
    admin = _make_admin(permissions={"users": {"read": SCOPE_NONE}})
    with pytest.raises(PermissionDenied):
        enforce_permission(admin, "users", "read")  # explicitly disabled


# --- enforce_scope ---


def test_owner_bypasses_scope():
    admin = _make_admin(is_owner=True, admin_id=1)
    enforce_scope(admin, "users", "read", target_admin_id=99)  # should not raise


def test_scope_own_allows_own_users():
    admin = _make_admin(permissions={"users": {"read": SCOPE_OWN}}, admin_id=10)
    enforce_scope(admin, "users", "read", target_admin_id=10)  # should not raise


def test_scope_own_denies_other_users():
    admin = _make_admin(permissions={"users": {"read": SCOPE_OWN}}, admin_id=10)
    with pytest.raises(PermissionDenied):
        enforce_scope(admin, "users", "read", target_admin_id=99)


def test_scope_all_allows_any_user():
    admin = _make_admin(permissions={"users": {"read": SCOPE_ALL}}, admin_id=10)
    enforce_scope(admin, "users", "read", target_admin_id=99)  # should not raise


def test_true_permission_no_scope_check():
    admin = _make_admin(permissions={"users": {"read": True}}, admin_id=10)
    enforce_scope(admin, "users", "read", target_admin_id=99)  # should not raise (True = no scope)


# --- get_effective_limits ---


def test_role_limits_returned_when_no_overrides():
    admin = _make_admin(limits={"max_users": 100, "data_limit_max": None})
    limits = get_effective_limits(admin)
    assert limits.max_users == 100


def test_non_null_override_wins():
    admin = _make_admin(
        limits={"max_users": 100},
        overrides={"max_users": 50},
    )
    limits = get_effective_limits(admin)
    assert limits.max_users == 50


def test_null_override_does_not_override():
    admin = _make_admin(
        limits={"max_users": 100},
        overrides={"max_users": None},
    )
    limits = get_effective_limits(admin)
    assert limits.max_users == 100


def test_no_role_returns_empty():
    admin = AdminDetails(username="x", role=None)
    limits = get_effective_limits(admin)
    assert limits.max_users is None  # RoleLimits with all None fields


def test_owner_has_all_groups():
    admin = _make_admin(is_owner=True, access={"allowed_group_ids": [1, 2]})
    assert get_allowed_group_ids(admin) is None


def test_role_group_restriction():
    admin = _make_admin(access={"allowed_group_ids": [1, 2, 3]})
    assert get_allowed_group_ids(admin) == [1, 2, 3]


def test_admin_group_override_intersects_role():
    admin = _make_admin(
        access={"allowed_group_ids": [1, 2, 3]},
        access_overrides={"allowed_group_ids": [2, 3, 4]},
    )
    assert get_allowed_group_ids(admin) == [2, 3]


def test_admin_group_override_when_role_unrestricted():
    admin = _make_admin(
        access={"allowed_group_ids": None},
        access_overrides={"allowed_group_ids": [5, 6]},
    )
    assert get_allowed_group_ids(admin) == [5, 6]
