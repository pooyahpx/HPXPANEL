from __future__ import annotations

from ipaddress import ip_address

from app.core.credential_vpn import CredentialVpnConfig
from app.db.models import CoreType
from app.models.protocol import ProxyProtocol


class GREConfig(CredentialVpnConfig):
    core_type = CoreType.gre
    protocol = ProxyProtocol.gre
    default_port = 0
    network = "ip"
    require_pool = True

    def _validate_common(self) -> None:
        # GRE is not port-based; allow port 0 / omit.
        if self.get("port") in (None, ""):
            self["port"] = 0
        super()._validate_common()
        if self["port"] != 0:
            raise ValueError("GRE does not use a TCP/UDP port; set port to 0")

    def _validate_backend(self) -> None:
        if not self["server_addr"]:
            raise ValueError("server_addr is required")
        peer = self._required_string("peer_addr")
        try:
            self["peer_addr"] = str(ip_address(peer))
        except ValueError as exc:
            raise ValueError("peer_addr must be a valid IP address") from exc

        local = self._optional_string("local_addr")
        if local:
            try:
                self["local_addr"] = str(ip_address(local))
            except ValueError as exc:
                raise ValueError("local_addr must be a valid IP address") from exc

        self["ipsec"] = bool(self.get("ipsec", False))
        fou_port = self.get("fou_port")
        if fou_port in (None, "", 0):
            self.pop("fou_port", None)
        else:
            if not isinstance(fou_port, int) or fou_port <= 0 or fou_port > 65535:
                raise ValueError("fou_port must be between 1 and 65535")
            self["fou_port"] = fou_port

    def _metadata(self) -> dict:
        meta = super()._metadata()
        meta.update(
            {
                "peer_addr": self["peer_addr"],
                "local_addr": self.get("local_addr", ""),
                "ipsec": bool(self.get("ipsec", False)),
            }
        )
        if "fou_port" in self:
            meta["fou_port"] = self["fou_port"]
        return meta
