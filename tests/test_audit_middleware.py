import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.app_factory import create_app
from app.middlewares import setup_middleware
from app.middlewares.audit import (
    _TARGETS,
    AuditMiddleware,
    _infer_action,
    _match_target,
    _path_parts,
    _resource_identifier,
)
from config import server_settings


@pytest.mark.parametrize(
    ("method", "path", "resource", "action"),
    [
        ("POST", "/api/user", "user", "create"),
        ("PUT", "/api/user/by-id/42", "user", "update"),
        ("POST", "/api/admins/bulk/disable", "admin", "bulk_disable"),
        ("PUT", "/api/admin/by-id/7", "admin", "update"),
        ("POST", "/api/admin-role", "admin_role", "create"),
        ("POST", "/api/api_key/9/revoke", "api_key", "revoke"),
        ("POST", "/api/node/3/reconnect", "node", "reconnect"),
        ("POST", "/api/core/4/restart", "core", "restart"),
        ("POST", "/api/hpx_tunnels/bulk/delete", "hpx_tunnel", "bulk_delete"),
        ("POST", "/api/hpx_tunnel/5/restart", "hpx_tunnel", "restart"),
        ("POST", "/api/hpx_tunnel/5/repair", "hpx_tunnel", "repair"),
        ("POST", "/api/hpx_pulse/6/join-token", "hpx_pulse", "join_token"),
        ("POST", "/api/hpx_pulse/6/sync", "hpx_pulse", "sync"),
        ("POST", "/api/cores/bulk/delete", "core", "bulk_delete"),
        ("POST", "/api/backup/nightly/restore", "backup", "restore"),
    ],
)
def test_sensitive_route_classification(method, path, resource, action):
    target = _match_target(path, method)
    assert target is not None
    assert target.resource == resource
    parts = _path_parts(path, target)
    resource_id = _resource_identifier(parts, None)
    assert _infer_action(method, parts, resource_id) == action


@pytest.mark.parametrize(
    "path",
    [
        "/api/admin/token",
        "/api/admin/miniapp/token",
        "/api/hpx_pulse/agent/claim",
        "/api/hpx_pulse/agent/heartbeat",
        "/api/hpx_pulse/agent/ack",
        "/api/hpx_tunnel/agent/claim",
        "/api/hpx_tunnel/agent/heartbeat",
        "/api/hpx_tunnel/agent/ack",
        "/api/backup/run",
    ],
)
def test_non_admin_or_non_restore_operations_are_not_audited(path):
    assert _match_target(path, "POST") is None


def test_all_targets_and_sensitive_mutations_match_actual_fastapi_routes():
    spec = create_app().openapi()
    mutation_methods = {"post", "put", "patch", "delete"}
    actual_mutations = {
        (method.upper(), path)
        for path, operations in spec["paths"].items()
        for method in operations
        if method in mutation_methods
    }

    for target in _TARGETS:
        assert any(path == target.prefix or path.startswith(f"{target.prefix}/") for _, path in actual_mutations)
        assert "-" not in target.prefix.removeprefix("/api/admin-role")

    sensitive_prefixes = (
        "/api/admin",
        "/api/admins",
        "/api/api_key",
        "/api/api_keys",
        "/api/backup",
        "/api/core",
        "/api/cores",
        "/api/hpx_pulse",
        "/api/hpx_tunnel",
        "/api/hpx_tunnels",
        "/api/node",
        "/api/nodes",
        "/api/user",
        "/api/users",
    )
    for method, path in actual_mutations:
        if not any(path == prefix or path.startswith(f"{prefix}/") for prefix in sensitive_prefixes):
            continue
        excluded = (
            path in {"/api/admin/token", "/api/admin/miniapp/token"}
            or path.startswith(("/api/hpx_pulse/agent/", "/api/hpx_tunnel/agent/"))
            or (path.startswith("/api/backup") and not path.endswith("/restore"))
        )
        assert (_match_target(path, method) is None) is excluded, f"{method} {path}"


def test_proxy_headers_normalize_source_ip_before_audit(monkeypatch):
    events = []

    async def capture_event(**kwargs):
        events.append(kwargs)

    monkeypatch.setattr("app.middlewares.audit.record_audit_log", capture_event)
    monkeypatch.setattr(server_settings, "has_ssl", False)
    monkeypatch.setattr(server_settings, "proxy_headers", True)
    monkeypatch.setattr(server_settings, "forwarded_allow_ips", "*")

    app = FastAPI()

    @app.post("/api/user")
    async def mutate_user():
        return {"id": 1}

    setup_middleware(app)
    assert app.user_middleware[0].cls.__name__ == "ProxyHeadersMiddleware"

    with TestClient(app) as test_client:
        response = test_client.post(
            "/api/user",
            json={"username": "forwarded-user"},
            headers={"X-Forwarded-For": "203.0.113.17", "X-Forwarded-Proto": "https"},
        )

    assert response.status_code == 200
    assert events[-1]["source_ip"] == "203.0.113.17"


def test_unhandled_exception_detail_never_includes_exception_text(monkeypatch):
    events = []
    raw_secret = "raw-unstructured-secret-42"

    async def capture_event(**kwargs):
        events.append(kwargs)

    monkeypatch.setattr("app.middlewares.audit.record_audit_log", capture_event)
    app = FastAPI()

    @app.post("/api/user")
    async def explode():
        raise RuntimeError(raw_secret)

    app.add_middleware(AuditMiddleware)
    with TestClient(app, raise_server_exceptions=False) as test_client:
        response = test_client.post("/api/user", json={"username": "failure-user"})

    assert response.status_code == 500
    assert events[-1]["result"] == "failure"
    assert events[-1]["detail"] == "RuntimeError"
    assert raw_secret not in str(events[-1])
