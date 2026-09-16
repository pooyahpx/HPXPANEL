from __future__ import annotations

from copy import deepcopy

from app.core.wireguard import WireGuardConfig
from app.db.models import CoreType
from app.models.protocol import ProxyProtocol

_AMNEZIA_PROTOCOLS = frozenset((ProxyProtocol.amneziawg,))
_OBFUSCATION_FIELDS = ("jc", "jmin", "jmax", "s1", "s2", "h1", "h2", "h3", "h4")
_OBFUSCATION_DEFAULTS = {
    "jc": 4,
    "jmin": 40,
    "jmax": 70,
    "s1": 0,
    "s2": 0,
    "h1": 1,
    "h2": 2,
    "h3": 3,
    "h4": 4,
}


class AmneziaWGConfig(WireGuardConfig):
    """Obfuscated WireGuard-compatible backend with junk-packet parameters."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._type = CoreType.amneziawg

    def _validate(self):
        super()._validate()
        for field, default in _OBFUSCATION_DEFAULTS.items():
            value = self.get(field, default)
            if not isinstance(value, int) or value < 0:
                raise ValueError(f"{field} must be a non-negative integer")
            self[field] = value
        if self["jmin"] > self["jmax"]:
            raise ValueError("jmin cannot be greater than jmax")
        if self["jc"] < 1 or self["jc"] > 128:
            raise ValueError("jc must be between 1 and 128")

    def _resolve_inbounds(self):
        super()._resolve_inbounds()
        for meta in self._inbounds_by_tag.values():
            meta["protocol"] = "amneziawg"
            for field in _OBFUSCATION_FIELDS:
                meta[field] = self[field]

    @property
    def protocols(self) -> frozenset[ProxyProtocol]:
        return _AMNEZIA_PROTOCOLS

    @classmethod
    def from_json(cls, data: dict) -> AmneziaWGConfig:
        instance = cls(config=data.get("config", {}), skip_validation=True)
        if "inbounds" in data:
            instance._inbounds = list(data["inbounds"])
        if "inbounds_by_tag" in data:
            instance._inbounds_by_tag = deepcopy(data["inbounds_by_tag"])
        return instance
