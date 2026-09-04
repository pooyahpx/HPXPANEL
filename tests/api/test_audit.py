import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import status
from sqlalchemy import select

from app.db.models import AuditLog
from app.services.audit import REDACTED, record_audit_log, redact
from tests.api import TestSession, client
from tests.api.helpers import auth_headers, create_admin, delete_admin, strong_password, unique_name


@pytest.fixture(autouse=True)
def use_test_audit_session(monkeypatch):
    from tests.api import GetTestDB

    monkeypatch.setattr("app.services.audit.GetDB", GetTestDB)
    monkeypatch.setattr("app.middlewares.audit.GetDB", GetTestDB)


def _login(username: str, password: str) -> str:
    response = client.post(
        "/api/admin/token",
        data={"username": username, "password": password, "grant_type": "password"},
    )
    assert response.status_code == status.HTTP_200_OK
    return response.json()["access_token"]


def _role_payload(name: str, permissions: dict) -> dict:
    return {
        "name": name,
        "permissions": permissions,
        "limits": {},
        "features": {"can_use_reset_strategy": True, "can_use_next_plan": True},
        "access": {"require_template": False, "allowed_template_ids": None, "allowed_group_ids": None},
        "hwid": {"mode": "use_global"},
    }


def test_recursive_redaction_covers_nested_and_inline_secrets():
    value = {
        "username": "safe",
        "password": "top-secret",
        "key": "generic-secret-key",
        "nested": [
            {"apiKey": "plain-key", "ok": 1},
            "Authorization: Bearer abc.def.ghi",
            {"join_token_hash": "hash"},
        ],
    }
    output = redact(value)
    assert output["username"] == "safe"
    assert output["password"] == REDACTED
    assert output["key"] == REDACTED
    assert output["nested"][0]["apiKey"] == REDACTED
    assert "abc.def.ghi" not in output["nested"][1]
    assert output["nested"][2]["join_token_hash"] == REDACTED


def test_owner_filters_pagination_details_and_csv_export(access_token):
    marker = unique_name("audit_action")
    asyncio.run(
        record_audit_log(
            action=marker,
            resource="test_resource",
            result="success",
            actor_username="testadmin",
            resource_id="=formula",
            after={"safe": "value", "token": "must-not-leak"},
        )
    )

    response = client.get(
        "/api/audit",
        headers=auth_headers(access_token),
        params={"action": marker, "result": "success", "offset": 0, "limit": 1},
    )
    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert payload["total"] == 1
    assert len(payload["logs"]) == 1
    assert payload["logs"][0]["after"]["token"] == REDACTED
    created_at = datetime.fromisoformat(payload["logs"][0]["created_at"])
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    fully_filtered = client.get(
        "/api/audit",
        headers=auth_headers(access_token),
        params={
            "search": marker,
            "actor": "testadmin",
            "action": marker,
            "resource": "test_resource",
            "result": "success",
            "start": (created_at - timedelta(seconds=1)).isoformat(),
            "end": (created_at + timedelta(seconds=1)).isoformat(),
        },
    )
    assert fully_filtered.status_code == status.HTTP_200_OK
    assert fully_filtered.json()["total"] == 1

    detail = client.get(f"/api/audit/{payload['logs'][0]['id']}", headers=auth_headers(access_token))
    assert detail.status_code == status.HTTP_200_OK
    assert detail.json()["action"] == marker

    export = client.get("/api/audit/export", headers=auth_headers(access_token), params={"action": marker})
    assert export.status_code == status.HTTP_200_OK
    assert export.headers["content-type"].startswith("text/csv")
    assert "attachment;" in export.headers["content-disposition"]
    assert "'=formula" in export.text
    assert "must-not-leak" not in export.text


def test_audit_permission_denied_and_delegated(access_token):
    denied_admin = create_admin(access_token, role_id=3)
    role_id = None
    delegated_admin = None
    try:
        denied_token = _login(denied_admin["username"], denied_admin["password"])
        denied = client.get("/api/audit", headers=auth_headers(denied_token))
        assert denied.status_code == status.HTTP_403_FORBIDDEN

        role_response = client.post(
            "/api/admin-role",
            headers=auth_headers(access_token),
            json=_role_payload(unique_name("auditor"), {"audit_logs": {"read": True}}),
        )
        assert role_response.status_code == status.HTTP_201_CREATED
        role_id = role_response.json()["id"]
        delegated_admin = create_admin(access_token, role_id=role_id)
        delegated_token = _login(delegated_admin["username"], delegated_admin["password"])
        allowed = client.get("/api/audit", headers=auth_headers(delegated_token))
        assert allowed.status_code == status.HTTP_200_OK
    finally:
        if delegated_admin:
            delete_admin(access_token, delegated_admin["username"])
        if role_id:
            client.delete(f"/api/admin-role/{role_id}", headers=auth_headers(access_token))
        delete_admin(access_token, denied_admin["username"])


def test_admin_mutation_success_failure_and_no_secret(access_token):
    username = unique_name("audited_admin")
    password = strong_password("AuditMutation")
    created = client.post(
        "/api/admin",
        headers=auth_headers(access_token),
        json={"username": username, "password": password, "role_id": 3},
    )
    assert created.status_code == status.HTTP_201_CREATED

    duplicate = client.post(
        "/api/admin",
        headers=auth_headers(access_token),
        json={"username": username, "password": password, "role_id": 3},
    )
    assert duplicate.status_code == status.HTTP_409_CONFLICT

    response = client.get(
        "/api/audit",
        headers=auth_headers(access_token),
        params={"resource": "admin", "action": "create", "limit": 20},
    )
    assert response.status_code == status.HTTP_200_OK
    logs = response.json()["logs"]
    matching = [log for log in logs if log.get("after", {}).get("request", {}).get("username") == username]
    assert {log["result"] for log in matching} == {"success", "failure"}
    assert password not in str(matching)
    assert all(log["after"]["request"]["password"] == REDACTED for log in matching)
    delete_admin(access_token, username)


def test_actual_hpx_pulse_mutation_route_is_audited(access_token):
    missing_pulse_id = 2_147_483_647
    mutation = client.post(
        f"/api/hpx_pulse/{missing_pulse_id}/sync",
        headers=auth_headers(access_token),
    )
    assert mutation.status_code == status.HTTP_404_NOT_FOUND

    response = client.get(
        "/api/audit",
        headers=auth_headers(access_token),
        params={"resource": "hpx_pulse", "action": "sync", "result": "failure", "limit": 20},
    )
    assert response.status_code == status.HTTP_200_OK
    assert any(log["resource_id"] == str(missing_pulse_id) for log in response.json()["logs"])


def test_audit_rows_are_append_only():
    async def exercise():
        async with TestSession() as db:
            log = AuditLog(action="test", resource="test", result="success")
            db.add(log)
            await db.commit()
            log_id = log.id
            log.action = "changed"
            try:
                await db.commit()
            except ValueError as exc:
                assert "append-only" in str(exc)
                await db.rollback()
            else:
                raise AssertionError("AuditLog update unexpectedly succeeded")

            persisted = (await db.execute(select(AuditLog).where(AuditLog.id == log_id))).scalar_one()
            assert persisted.action == "test"
            await db.delete(persisted)
            try:
                await db.commit()
            except ValueError as exc:
                assert "append-only" in str(exc)
                await db.rollback()
            else:
                raise AssertionError("AuditLog delete unexpectedly succeeded")

    asyncio.run(exercise())
