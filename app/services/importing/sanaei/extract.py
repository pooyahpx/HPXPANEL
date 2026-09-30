"""Extract Sanaei / 3x-ui SQLite (x-ui.db) into an ImportPlan."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from app.services.importing.types import ImportGroupDraft, ImportHostDraft, ImportPlan, ImportSource, ImportUserDraft
from app.services.importing.util import as_datetime, coerce_uuid, parse_json_obj, sanitize_username, unique_name


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND lower(name)=lower(?) LIMIT 1",
        (name,),
    ).fetchone()
    return row is not None


def _rows(conn: sqlite3.Connection, table: str) -> list[dict[str, Any]]:
    cur = conn.execute(f"SELECT * FROM {table}")
    names = [d[0] for d in cur.description]
    return [dict(zip(names, row, strict=False)) for row in cur.fetchall()]


def _protocol_proxy_settings(protocol: str, client: dict[str, Any]) -> dict[str, Any]:
    protocol = (protocol or "vless").lower().strip()
    settings: dict[str, Any] = {}
    client_id = coerce_uuid(client.get("id"))
    password = client.get("password") or client.get("pass") or ""

    if protocol == "vmess":
        settings["vmess"] = {"id": client_id} if client_id else {}
    elif protocol == "vless":
        settings["vless"] = {"id": client_id} if client_id else {}
    elif protocol == "trojan":
        settings["trojan"] = {"password": str(password or client_id or "")}
    elif protocol in {"shadowsocks", "ss"}:
        method = client.get("method") or "chacha20-ietf-poly1305"
        settings["shadowsocks"] = {
            "password": str(password or client.get("id") or "changeme-password-xx"),
            "method": method,
        }
    else:
        # Best-effort: stash as vless if uuid present
        if client_id:
            settings["vless"] = {"id": client_id}
        elif password:
            settings["trojan"] = {"password": str(password)}
    return settings


def _merge_proxy(dst: dict[str, Any], src: dict[str, Any]) -> dict[str, Any]:
    out = dict(dst)
    for key, value in src.items():
        if key not in out or not out[key]:
            out[key] = value
    return out


def extract_sanaei(db_path: Path) -> ImportPlan:
    plan = ImportPlan(source=ImportSource.sanaei)
    plan.notes.append("Sanaei/3x-ui clients are mapped to HPXPANEL users (email → username).")
    plan.notes.append("Subscription URLs will be new HPXPANEL links after import.")
    plan.notes.append("Core Xray JSON is not fully merged — attach imported groups to an existing core/inbounds.")

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        if not _table_exists(conn, "inbounds"):
            plan.warnings.append("No inbounds table in 3x-ui database")
            return plan

        traffic_by_email: dict[str, dict[str, Any]] = {}
        if _table_exists(conn, "client_traffics"):
            for row in _rows(conn, "client_traffics"):
                email = str(row.get("email") or "").strip()
                if not email:
                    continue
                traffic_by_email[email.lower()] = row

        users_by_name: dict[str, ImportUserDraft] = {}
        used_names: set[str] = set()
        used_tags: set[str] = set()

        for inbound in _rows(conn, "inbounds"):
            protocol = str(inbound.get("protocol") or "vless")
            remark = str(inbound.get("remark") or inbound.get("tag") or f"inbound-{inbound.get('id')}")
            raw_tag = sanitize_username(remark, fallback=f"inbound-{inbound.get('id')}")
            if len(raw_tag) < 3:
                raw_tag = f"in-{raw_tag}"
            tag = unique_name(f"3xui-{raw_tag}", used_tags)

            listen = str(inbound.get("listen") or "").strip() or None
            port = inbound.get("port")
            try:
                port_i = int(port) if port not in (None, "") else None
            except (TypeError, ValueError):
                port_i = None

            stream = parse_json_obj(inbound.get("stream_settings"), {})
            if not isinstance(stream, dict):
                stream = {}
            network = str(stream.get("network") or "tcp")
            security = str(stream.get("security") or "none").lower()
            path = None
            sni: set[str] = set()
            host_hdr: set[str] = set()
            allowinsecure = None

            ws = stream.get("wsSettings") if isinstance(stream.get("wsSettings"), dict) else {}
            grpc = stream.get("grpcSettings") if isinstance(stream.get("grpcSettings"), dict) else {}
            tcp = stream.get("tcpSettings") if isinstance(stream.get("tcpSettings"), dict) else {}
            reality = stream.get("realitySettings") if isinstance(stream.get("realitySettings"), dict) else {}
            tls = stream.get("tlsSettings") if isinstance(stream.get("tlsSettings"), dict) else {}

            if network == "ws":
                path = ws.get("path")
                headers = ws.get("headers") if isinstance(ws.get("headers"), dict) else {}
                if headers.get("Host"):
                    host_hdr.add(str(headers["Host"]))
            elif network == "grpc":
                path = grpc.get("serviceName")
            elif network == "tcp":
                header = tcp.get("header") if isinstance(tcp.get("header"), dict) else {}
                req = header.get("request") if isinstance(header.get("request"), dict) else {}
                if isinstance(req.get("path"), list) and req["path"]:
                    path = str(req["path"][0])

            if security == "reality":
                server_names = reality.get("serverNames") or reality.get("server_names") or []
                if isinstance(server_names, list):
                    sni = {str(x) for x in server_names if x}
                dest = reality.get("dest") or reality.get("target")
                if isinstance(dest, str) and ":" in dest:
                    # ignore
                    pass
            elif security == "tls":
                server_name = tls.get("serverName")
                if server_name:
                    sni.add(str(server_name))
                allowinsecure = bool(tls.get("allowInsecure")) if "allowInsecure" in tls else None

            hpx_security = "inbound_default"
            if security == "tls":
                hpx_security = "tls"
            elif security == "reality":
                hpx_security = "reality"
            elif security == "none":
                hpx_security = "none"

            address = {listen} if listen and listen not in {"0.0.0.0", "::", ""} else set()
            if not address:
                address = {"CHANGE_ME"}
                plan.warnings.append(
                    f"Host '{remark}' has no public address — set address after import (placeholder CHANGE_ME)."
                )

            plan.hosts.append(
                ImportHostDraft(
                    remark=remark[:64] or tag,
                    address=address,
                    inbound_tag=tag,
                    port=port_i,
                    sni=sni,
                    host=host_hdr,
                    path=str(path) if path else None,
                    security=hpx_security,
                    allowinsecure=allowinsecure,
                    is_disabled=not bool(inbound.get("enable", 1)),
                    priority=int(inbound.get("id") or 0),
                    meta={"protocol": protocol, "network": network},
                )
            )
            plan.groups.append(
                ImportGroupDraft(
                    name=tag if len(tag) >= 3 else f"grp-{tag}",
                    inbound_tags=[tag],
                    is_disabled=not bool(inbound.get("enable", 1)),
                    source_id=int(inbound["id"]) if inbound.get("id") is not None else None,
                )
            )

            settings = parse_json_obj(inbound.get("settings"), {})
            clients = settings.get("clients") if isinstance(settings, dict) else None
            if not isinstance(clients, list):
                clients = []

            for client in clients:
                if not isinstance(client, dict):
                    continue
                email = str(client.get("email") or client.get("email_") or "").strip()
                if not email:
                    # fallback to id fragment
                    email = str(client.get("id") or client.get("password") or "client")[:32]
                base_name = sanitize_username(email)
                username = unique_name(base_name, used_names)

                traffic = traffic_by_email.get(email.lower(), {})
                up = int(traffic.get("up") or 0)
                down = int(traffic.get("down") or 0)
                total = traffic.get("total")
                if total in (None, ""):
                    total = client.get("totalGB") or client.get("total") or 0
                try:
                    total_i = int(total or 0)
                except (TypeError, ValueError):
                    total_i = 0
                # 3x-ui totalGB is sometimes in GB not bytes — if small, treat as GB
                if total_i > 0 and total_i < 10_000:
                    total_i = total_i * 1024 * 1024 * 1024

                expiry = traffic.get("expiry_time")
                if expiry in (None, "", 0, "0"):
                    expiry = client.get("expiryTime") or client.get("expiry_time")

                enable = client.get("enable", True)
                if traffic.get("enable") is not None:
                    enable = traffic.get("enable")

                proxy = _protocol_proxy_settings(protocol, client)
                existing = users_by_name.get(username)
                if existing:
                    existing.proxy_settings = _merge_proxy(existing.proxy_settings, proxy)
                    if tag not in existing.source_inbound_tags:
                        existing.source_inbound_tags.append(tag)
                    existing.source_group_names.append(tag)
                    existing.used_traffic = max(existing.used_traffic, up + down)
                    continue

                users_by_name[username] = ImportUserDraft(
                    username=username,
                    proxy_settings=proxy,
                    status="active" if enable else "disabled",
                    data_limit=total_i if total_i > 0 else None,
                    used_traffic=max(0, up + down),
                    expire=as_datetime(expiry),
                    note=f"imported from 3x-ui inbound '{remark}'",
                    source_group_names=[tag],
                    source_inbound_tags=[tag],
                    meta={"email": email, "protocol": protocol},
                )

        plan.users = list(users_by_name.values())
    finally:
        conn.close()

    if not plan.users:
        plan.warnings.append("No clients extracted from 3x-ui database")
    return plan
