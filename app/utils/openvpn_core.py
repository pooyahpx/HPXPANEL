from __future__ import annotations

from typing import Any


def openvpn_pki_ready(config: dict[str, Any] | None) -> bool:
    if not config:
        return False
    ca_cert = str(config.get("ca_cert") or "").strip()
    ca_key = str(config.get("ca_key") or "").strip()
    server_cert = str(config.get("server_cert") or "").strip()
    server_key = str(config.get("server_key") or "").strip()
    if not ca_cert or not server_cert or not server_key:
        return False
    return bool(ca_key)


def openvpn_ca_key_missing(config: dict[str, Any] | None) -> bool:
    if not config:
        return False
    ca_cert = str(config.get("ca_cert") or "").strip()
    ca_key = str(config.get("ca_key") or "").strip()
    return bool(ca_cert) and not bool(ca_key)
