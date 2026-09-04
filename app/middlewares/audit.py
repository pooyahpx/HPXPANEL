from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.db import GetDB
from app.db.models import Admin, AdminRole, APIKey, CoreConfig, HpxPulse, HpxTunnel, Node, User
from app.services.audit import model_snapshot, record_audit_log, redact
from app.utils.jwt import get_admin_payload

_MAX_CAPTURE_BYTES = 1024 * 1024


@dataclass(frozen=True)
class AuditTarget:
    prefix: str
    resource: str
    model: type
    name_column: str | None = None


_TARGETS = (
    AuditTarget("/api/admins", "admin", Admin, "username"),
    AuditTarget("/api/api_keys", "api_key", APIKey),
    AuditTarget("/api/cores", "core", CoreConfig, "name"),
    AuditTarget("/api/users", "user", User, "username"),
    AuditTarget("/api/nodes", "node", Node, "name"),
    AuditTarget("/api/admin-role", "admin_role", AdminRole),
    AuditTarget("/api/api_key", "api_key", APIKey),
    AuditTarget("/api/hpx_tunnels", "hpx_tunnel", HpxTunnel),
    AuditTarget("/api/hpx_pulse", "hpx_pulse", HpxPulse),
    AuditTarget("/api/hpx_tunnel", "hpx_tunnel", HpxTunnel),
    AuditTarget("/api/backup", "backup", object),
    AuditTarget("/api/user", "user", User, "username"),
    AuditTarget("/api/admin", "admin", Admin, "username"),
    AuditTarget("/api/node", "node", Node, "name"),
    AuditTarget("/api/core", "core", CoreConfig, "name"),
)
_NON_TARGET_SEGMENTS = {
    "",
    "s",
    "bulk",
    "from_template",
    "reality-scan",
    "openvpn",
    "agent",
    "token",
    "miniapp",
    "config",
    "run",
    "import",
}
_ACTION_SEGMENTS = {
    "activate",
    "advise",
    "claim",
    "core_update",
    "delete",
    "diagnose",
    "disable",
    "enable",
    "expire",
    "geofiles",
    "groups",
    "import",
    "join-token",
    "proxy",
    "reconnect",
    "repair",
    "reset",
    "restart",
    "restore",
    "revoke",
    "set_owner",
    "smart-fix",
    "start",
    "stop",
    "sync",
    "update",
    "users",
}


def _headers(scope: Scope) -> dict[str, str]:
    return {
        key.decode("latin-1").lower(): value.decode("latin-1")
        for key, value in scope.get("headers", [])
    }


def _match_target(path: str, method: str) -> AuditTarget | None:
    if method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return None
    for target in _TARGETS:
        if path == target.prefix or path.startswith(f"{target.prefix}/"):
            if target.resource == "admin" and path in {"/api/admin/token", "/api/admin/miniapp/token"}:
                return None
            if target.resource in {"hpx_pulse", "hpx_tunnel"} and "/agent/" in path:
                return None
            if target.resource == "backup" and not path.endswith("/restore"):
                return None
            return target
    return None


def _parse_json(data: bytes, content_type: str) -> Any:
    if not data or "json" not in content_type.lower() or len(data) > _MAX_CAPTURE_BYTES:
        return None
    try:
        return json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


def _path_parts(path: str, target: AuditTarget) -> list[str]:
    return [part for part in path.removeprefix(target.prefix).strip("/").split("/") if part]


def _resource_identifier(parts: list[str], body: Any) -> str | None:
    if "by-id" in parts:
        index = parts.index("by-id")
        return parts[index + 1] if len(parts) > index + 1 else None
    if "by-username" in parts:
        index = parts.index("by-username")
        return parts[index + 1] if len(parts) > index + 1 else None
    if "bulk" in parts and isinstance(body, dict):
        ids = body.get("ids") or body.get("user_ids") or body.get("admin_ids")
        if isinstance(ids, list):
            return ",".join(str(item) for item in ids[:100])
    if parts and parts[0] not in _NON_TARGET_SEGMENTS and parts[0] not in _ACTION_SEGMENTS:
        return parts[0]
    return None


def _infer_action(method: str, parts: list[str], resource_id: str | None) -> str:
    tail = next((part for part in reversed(parts) if part in _ACTION_SEGMENTS), None)
    if "bulk" in parts:
        return f"bulk_{tail or method.lower()}"[:64]
    if tail and not (tail == "users" and resource_id):
        return tail.replace("-", "_")
    if method == "DELETE":
        return "delete"
    if method in {"PUT", "PATCH"}:
        return "update"
    return "update" if resource_id else "create"


async def _resolve_actor(headers: dict[str, str]) -> tuple[int | None, str | None]:
    authorization = headers.get("authorization", "")
    scheme, _, credentials = authorization.partition(" ")
    if scheme.lower() == "bearer" and credentials:
        try:
            payload = await get_admin_payload(credentials.strip())
            if payload:
                return payload.get("admin_id"), payload.get("username")
        except Exception:
            pass

    raw_api_key = headers.get("x-api-key")
    if not raw_api_key and scheme.lower() == "apikey":
        raw_api_key = credentials.strip()
    if raw_api_key:
        try:
            from app.routers.authentication import get_admin_from_api_key

            async with GetDB() as db:
                admin = await get_admin_from_api_key(db, raw_api_key)
                if admin:
                    return admin.id, admin.username
        except Exception:
            pass
    return None, None


async def _snapshot(target: AuditTarget, resource_id: str | None, body: Any) -> Any:
    if target.model is object or resource_id is None:
        return None
    identifiers = resource_id.split(",")
    snapshots: list[dict[str, Any]] = []
    try:
        async with GetDB() as db:
            for identifier in identifiers[:100]:
                if identifier.isdigit():
                    condition = target.model.id == int(identifier)
                elif target.name_column:
                    condition = getattr(target.model, target.name_column) == identifier
                else:
                    continue
                instance = (await db.execute(select(target.model).where(condition))).scalar_one_or_none()
                snapshot = model_snapshot(instance)
                if snapshot is not None:
                    snapshots.append(snapshot)
    except Exception:
        return None
    if not snapshots:
        return None
    return snapshots[0] if len(identifiers) == 1 else snapshots


class AuditMiddleware:
    """Capture sensitive admin mutations without sharing their database transaction."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        method = scope.get("method", "GET").upper()
        target = _match_target(path, method)
        if target is None:
            await self.app(scope, receive, send)
            return

        request_messages: list[Message] = []
        request_body = bytearray()
        while True:
            message = await receive()
            request_messages.append(message)
            if message["type"] == "http.request":
                request_body.extend(message.get("body", b""))
                if not message.get("more_body", False):
                    break
            else:
                break

        request_index = 0

        async def replay_receive() -> Message:
            nonlocal request_index
            if request_index < len(request_messages):
                message = request_messages[request_index]
                request_index += 1
                return message
            return {"type": "http.request", "body": b"", "more_body": False}

        headers = _headers(scope)
        request_json = _parse_json(bytes(request_body), headers.get("content-type", ""))
        parts = _path_parts(path, target)
        resource_id = _resource_identifier(parts, request_json)
        action = _infer_action(method, parts, resource_id)
        actor_id, actor_username = await _resolve_actor(headers)
        before = await _snapshot(target, resource_id, request_json)

        status_code = 500
        response_body = bytearray()

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message.get("status", 500))
            elif message["type"] == "http.response.body" and len(response_body) < _MAX_CAPTURE_BYTES:
                response_body.extend(message.get("body", b"")[: _MAX_CAPTURE_BYTES - len(response_body)])
            await send(message)

        raised: Exception | None = None
        try:
            await self.app(scope, replay_receive, send_wrapper)
        except Exception as exc:
            raised = exc
        finally:
            response_json = _parse_json(bytes(response_body), "application/json")
            result = "success" if raised is None and status_code < 400 else "failure"
            detail = None
            if result == "failure":
                if isinstance(response_json, dict):
                    raw_detail = response_json.get("detail") or response_json.get("error") or f"HTTP {status_code}"
                    safe_detail = redact(raw_detail)
                    detail = (
                        safe_detail
                        if isinstance(safe_detail, str)
                        else json.dumps(safe_detail, ensure_ascii=False, separators=(",", ":"))
                    )
                elif raised is not None:
                    detail = type(raised).__name__
                else:
                    detail = f"HTTP {status_code}"

            after_snapshot = await _snapshot(target, resource_id, request_json) if result == "success" else None
            if response_json is not None:
                after_data: Any = {"state": after_snapshot, "request": request_json, "response": response_json}
            else:
                after_data = {"state": after_snapshot, "request": request_json} if request_json or after_snapshot else None

            client = scope.get("client")
            await record_audit_log(
                action=action,
                resource=target.resource,
                result=result,
                actor_id=actor_id,
                actor_username=actor_username,
                source_ip=client[0] if client else None,
                resource_id=resource_id,
                before=before,
                after=redact(after_data),
                detail=detail,
            )

        if raised is not None:
            raise raised
