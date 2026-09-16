from __future__ import annotations

import json
from copy import deepcopy
from ipaddress import IPv4Network, ip_address, ip_network
from pathlib import PosixPath
from typing import ClassVar

import commentjson

from app.db.models import CoreType
from app.models.protocol import ProxyProtocol


class CredentialVpnConfig(dict):
    """Shared AbstractCore-compatible behavior for username/password VPN backends."""

    core_type: ClassVar[CoreType]
    protocol: ClassVar[ProxyProtocol]
    default_port: ClassVar[int] = 1723
    network: ClassVar[str] = "tcp"
    require_pool: ClassVar[bool] = True

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

        self._validate_common()
        self._validate_backend()
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

    def _string_list(self, field: str, default: tuple[str, ...] | list[str]) -> list[str]:
        value = self.get(field)
        if value in (None, []):
            return list(default)
        if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
            raise ValueError(f"{field} must be a list of non-empty strings")
        return [item.strip() for item in value]

    def _ip_list(self, field: str, default: tuple[str, ...] | list[str]) -> list[str]:
        values = self._string_list(field, default)
        try:
            return [str(ip_address(value)) for value in values]
        except ValueError as exc:
            raise ValueError(f"{field} must contain valid IP addresses") from exc

    def _validate_common(self) -> None:
        if self.exclude_inbound_tags:
            raise ValueError("exclude_inbound_tags is only supported for xray cores")
        if self.fallbacks_inbound_tags:
            raise ValueError("fallbacks_inbound_tags is only supported for xray cores")

        self["inbound_tag"] = self._required_string("inbound_tag")
        if "," in self["inbound_tag"] or "<=>" in self["inbound_tag"]:
            raise ValueError("inbound_tag cannot contain ',' or '<=>'")

        self["server_addr"] = self._optional_string("server_addr")

        port = self.get("port", self.default_port)
        if not isinstance(port, int) or port < 0 or port > 65535:
            raise ValueError("port must be between 0 and 65535")
        if port == 0 and self.default_port != 0:
            raise ValueError("port must be between 1 and 65535")
        self["port"] = port

        if self.require_pool:
            pool = self._required_string("pool")
            try:
                network = ip_network(pool, strict=False)
            except ValueError as exc:
                raise ValueError("pool must be a valid CIDR network") from exc
            if not isinstance(network, IPv4Network):
                raise ValueError("pool must be an IPv4 CIDR network")
            self["pool"] = str(network)
            self["dns"] = self._ip_list("dns", ["1.1.1.1", "8.8.8.8"])
        else:
            self.pop("pool", None)
            dns = self.get("dns")
            if dns not in (None, [], ""):
                self["dns"] = self._ip_list("dns", [])

    def _validate_backend(self) -> None:
        return

    def _metadata(self) -> dict:
        meta = {
            "tag": self["inbound_tag"],
            "protocol": self.protocol.name,
            "network": self.network,
            "tls": "none",
            "port": self["port"],
            "server_addr": self.get("server_addr", ""),
        }
        if "pool" in self:
            meta["pool"] = self["pool"]
        if "dns" in self:
            meta["dns"] = list(self["dns"])
        return meta

    def _resolve_inbounds(self) -> None:
        tag = self["inbound_tag"]
        self._inbounds = [tag]
        self._inbounds_by_tag = {tag: self._metadata()}

    def to_str(self, **json_kwargs) -> str:
        return json.dumps(self, **json_kwargs)

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
    def from_json(cls, data: dict) -> CredentialVpnConfig:
        instance = cls(config=data.get("config", {}), skip_validation=True)
        if "inbounds" in data:
            instance._inbounds = list(data["inbounds"])
        if "inbounds_by_tag" in data:
            instance._inbounds_by_tag = deepcopy(data["inbounds_by_tag"])
        return instance

    def copy(self):
        return deepcopy(self)
