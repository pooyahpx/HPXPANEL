from __future__ import annotations

import json
from copy import deepcopy
from ipaddress import IPv4Network, ip_address, ip_network
from pathlib import PosixPath
from typing import ClassVar

import commentjson

from app.db.models import CoreType
from app.models.protocol import ProxyProtocol


class IPsecConfig(dict):
    """Shared AbstractCore-compatible behavior for native IPsec backends."""

    core_type: ClassVar[CoreType]
    protocol: ClassVar[ProxyProtocol]
    default_ike_proposals: ClassVar[tuple[str, ...]]
    default_esp_proposals: ClassVar[tuple[str, ...]]

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

    def _validate_common(self) -> None:
        if self.exclude_inbound_tags:
            raise ValueError("exclude_inbound_tags is only supported for xray cores")
        if self.fallbacks_inbound_tags:
            raise ValueError("fallbacks_inbound_tags is only supported for xray cores")

        self["inbound_tag"] = self._required_string("inbound_tag")
        if "," in self["inbound_tag"] or "<=>" in self["inbound_tag"]:
            raise ValueError("inbound_tag cannot contain ',' or '<=>'")

        self["server_addr"] = self._optional_string("server_addr")
        self["egress_interface"] = self._optional_string("egress_interface")

        pool = self._required_string("pool")
        try:
            network = ip_network(pool, strict=False)
        except ValueError as exc:
            raise ValueError("pool must be a valid CIDR network") from exc
        if not isinstance(network, IPv4Network):
            raise ValueError("pool must be an IPv4 CIDR network")  # noqa: TRY004
        self["pool"] = str(network)

        self["dns"] = self._ip_list("dns", ["1.1.1.1", "8.8.8.8"])
        self["ike_proposals"] = self._string_list("ike_proposals", self.default_ike_proposals)
        self["esp_proposals"] = self._string_list("esp_proposals", self.default_esp_proposals)

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

    def _validate_backend(self) -> None:
        raise NotImplementedError

    def _metadata(self) -> dict:
        raise NotImplementedError

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
    def from_json(cls, data: dict) -> IPsecConfig:
        instance = cls(config=data.get("config", {}), skip_validation=True)
        if "inbounds" in data:
            instance._inbounds = list(data["inbounds"])
        if "inbounds_by_tag" in data:
            instance._inbounds_by_tag = deepcopy(data["inbounds_by_tag"])
        return instance

    def copy(self):
        return deepcopy(self)
