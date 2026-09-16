from __future__ import annotations

from copy import deepcopy

from app.core.wireguard import WireGuardConfig
from app.db.models import CoreType
from app.models.protocol import ProxyProtocol

_WG_C_PROTOCOLS = frozenset((ProxyProtocol.wg_c,))


class WireGuardCConfig(WireGuardConfig):
    """Kernel WireGuard backend (panel config schema mirrors userspace WG)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._type = CoreType.wg_c

    @property
    def protocols(self) -> frozenset[ProxyProtocol]:
        return _WG_C_PROTOCOLS

    def _resolve_inbounds(self):
        super()._resolve_inbounds()
        for meta in self._inbounds_by_tag.values():
            meta["protocol"] = "wg_c"
            meta["implementation"] = "kernel"

    @classmethod
    def from_json(cls, data: dict) -> WireGuardCConfig:
        instance = cls(config=data.get("config", {}), skip_validation=True)
        if "inbounds" in data:
            instance._inbounds = list(data["inbounds"])
        if "inbounds_by_tag" in data:
            instance._inbounds_by_tag = deepcopy(data["inbounds_by_tag"])
        return instance
