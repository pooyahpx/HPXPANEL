from __future__ import annotations

import json
from copy import deepcopy
from ipaddress import IPv4Network, ip_network
from pathlib import PosixPath
from typing import ClassVar

import commentjson

from app.db.models import CoreType
from app.models.protocol import ProxyProtocol

_VALID_PROTOS = frozenset({"udp", "tcp", "udp4", "udp6", "tcp4", "tcp6"})


class OpenVPNConfig(dict):
    """OpenVPN backend config — must match the HPX node's backend/openvpn/config.go schema."""

    core_type: ClassVar[CoreType] = CoreType.openvpn
    protocol: ClassVar[ProxyProtocol] = ProxyProtocol.openvpn

    def __init__(
        self,
        config: dict | str | PosixPath | None = None,
        exclude_inbound_tags: set[str] | None = None,
        fallbacks_inbound_tags: set[str] | None = None,
        skip_validation: bool = False,
    ):
        if config is None:
            config = {}
        if isinstance(config, str):
            config = commentjson.loads(config)
        if isinstance(config, dict):
            config = deepcopy(config)
        if not isinstance(config, dict):
            raise TypeError("config must be a dictionary or JSON string")

        super().__init__(config)
        self._type = self.core_type
        self.exclude_inbound_tags = set(exclude_inbound_tags or set())
        self.fallbacks_inbound_tags = set(fallbacks_inbound_tags or set())
        self._inbounds: list[str] = []
        self._inbounds_by_tag: dict[str, dict] = {}

        if skip_validation:
            return

        self._validate()
        self._resolve_inbounds()

    @property
    def type(self) -> CoreType:
        return self._type

    def _required_string(self, field: str) -> str:
        value = self.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field} is required")
        return value.strip()

    def _optional_string(self, field: str) -> str:
        value = self.get(field, "")
        if value is None:
            return ""
        if not isinstance(value, str):
            raise TypeError(f"{field} must be a string")
        return value.strip()

    def _string_list(self, field: str, default: tuple[str, ...] | list[str] | None = None) -> list[str]:
        value = self.get(field)
        if value in (None, []):
            return list(default or [])
        if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
            raise ValueError(f"{field} must be a list of non-empty strings")
        return [item.strip() for item in value]

    def _validate(self) -> None:
        if self.exclude_inbound_tags:
            raise ValueError("exclude_inbound_tags is only supported for xray cores")
        if self.fallbacks_inbound_tags:
            raise ValueError("fallbacks_inbound_tags is only supported for xray cores")

        self["inbound_tag"] = self._required_string("inbound_tag")
        if "," in self["inbound_tag"] or "<=>" in self["inbound_tag"]:
            raise ValueError("inbound_tag cannot contain ',' or '<=>'")

        port = self.get("port")
        if not isinstance(port, int) or port <= 0 or port > 65535:
            raise ValueError("port must be between 1 and 65535")

        proto = self._optional_string("proto") or "udp"
        proto = proto.lower()
        if proto not in _VALID_PROTOS:
            raise ValueError("proto must be udp or tcp")
        self["proto"] = proto

        device = self._optional_string("device") or "tun"
        self["device"] = device

        pool = self._required_string("server_subnet")
        try:
            network = ip_network(pool, strict=False)
        except ValueError as exc:
            raise ValueError("server_subnet must be a valid CIDR network") from exc
        if not isinstance(network, IPv4Network):
            raise ValueError("server_subnet must be an IPv4 CIDR network")  # noqa: TRY004
        self["server_subnet"] = str(network)

        self["dns"] = self._string_list("dns", ["1.1.1.1", "8.8.8.8"])
        self["cipher"] = self._optional_string("cipher") or "AES-256-GCM"
        self["data_ciphers"] = self._string_list("data_ciphers")
        self["auth"] = self._optional_string("auth") or "SHA256"
        self["keepalive"] = self._optional_string("keepalive") or "10 60"

        max_clients = self.get("max_clients")
        if max_clients in (None, ""):
            max_clients = 1024
        if not isinstance(max_clients, int) or max_clients <= 0:
            raise ValueError("max_clients must be a positive integer")
        self["max_clients"] = max_clients

        duplicate_cn = self.get("duplicate_cn", False)
        self["duplicate_cn"] = bool(duplicate_cn)

        self["push"] = self._string_list("push")
        self["extra_server_directives"] = self._string_list("extra_server_directives")

        self["ca_cert"] = self._required_string("ca_cert")
        self["server_cert"] = self._required_string("server_cert")
        self["server_key"] = self._required_string("server_key")
        self["tls_crypt_key"] = self._optional_string("tls_crypt_key")
        ca_key = self._optional_string("ca_key")
        if ca_key:
            self["ca_key"] = ca_key
        else:
            self.pop("ca_key", None)

        listeners = self.get("listeners")
        if listeners in (None, []):
            self["listeners"] = []
        else:
            if not isinstance(listeners, list):
                raise ValueError("listeners must be a list")
            normalized: list[dict[str, object]] = []
            seen: set[str] = set()
            for item in listeners:
                if not isinstance(item, dict):
                    raise TypeError("each listener must be an object")
                listener_port = item.get("port", self["port"])
                if not isinstance(listener_port, int) or listener_port <= 0 or listener_port > 65535:
                    raise ValueError("listener port must be between 1 and 65535")
                listener_proto = str(item.get("proto") or self["proto"]).lower()
                if listener_proto not in _VALID_PROTOS:
                    raise ValueError("listener proto must be udp or tcp")
                key = f"{listener_proto}/{listener_port}"
                if key in seen:
                    raise ValueError(f"duplicate listener {key}")
                seen.add(key)
                normalized.append({"port": listener_port, "proto": listener_proto})
            self["listeners"] = normalized

    def _metadata(self) -> dict:
        return {
            "tag": self["inbound_tag"],
            "protocol": "openvpn",
            "network": self["proto"],
            "tls": "none",
            "port": self["port"],
            "server_subnet": self["server_subnet"],
            "dns": list(self["dns"]),
        }

    def _resolve_inbounds(self) -> None:
        tag = self["inbound_tag"]
        self._inbounds = [tag]
        self._inbounds_by_tag = {tag: self._metadata()}

    def to_str(self, **json_kwargs) -> str:
        payload = dict(self)
        payload.pop("ca_key", None)
        return json.dumps(payload, **json_kwargs)

    @property
    def inbounds_by_tag(self) -> dict:
        return self._inbounds_by_tag

    @property
    def inbounds(self) -> list[str]:
        return self._inbounds

    @property
    def protocols(self) -> frozenset[ProxyProtocol]:
        return frozenset((self.protocol,))

    def to_json(self) -> dict:
        return {
            "type": self.type,
            "config": dict(self),
            "exclude_inbound_tags": [],
            "fallbacks_inbound_tags": [],
            "inbounds": self.inbounds,
            "inbounds_by_tag": self.inbounds_by_tag,
        }

    @classmethod
    def from_json(cls, data: dict) -> OpenVPNConfig:
        instance = cls(config=data.get("config", {}), skip_validation=True)
        if "inbounds" in data:
            instance._inbounds = list(data["inbounds"])
        if "inbounds_by_tag" in data:
            instance._inbounds_by_tag = deepcopy(data["inbounds_by_tag"])
        return instance

    def copy(self):
        return deepcopy(self)
