from app.core.ipsec import IPsecConfig
from app.db.models import CoreType
from app.models.protocol import ProxyProtocol


class IKEv2Config(IPsecConfig):
    core_type = CoreType.ikev2
    protocol = ProxyProtocol.ikev2
    default_ike_proposals = ("aes256-sha256-modp2048", "aes128-sha256-modp2048")
    default_esp_proposals = ("aes256-sha256", "aes128-sha256")

    def _validate_backend(self) -> None:
        if not self["server_addr"]:
            raise ValueError("server_addr is required")

        identity = self._optional_string("identity")
        self["identity"] = identity or self["server_addr"]

        for field in ("ca_cert", "server_cert", "server_key"):
            self[field] = self._required_string(field)

    def _metadata(self) -> dict:
        return {
            "tag": self["inbound_tag"],
            "protocol": "ikev2",
            "network": "udp",
            "tls": "none",
            "port": 500,
            "server_addr": self["server_addr"],
            "identity": self["identity"],
            "pool": self["pool"],
            "dns": list(self["dns"]),
        }
