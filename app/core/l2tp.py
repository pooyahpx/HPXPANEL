from ipaddress import ip_address, ip_network

from app.core.ipsec import IPsecConfig
from app.db.models import CoreType
from app.models.protocol import ProxyProtocol


class L2TPConfig(IPsecConfig):
    core_type = CoreType.l2tp
    protocol = ProxyProtocol.l2tp
    default_ike_proposals = (
        "aes256-sha1-modp2048",
        "aes128-sha1-modp1024",
        "3des-sha1-modp1024",
    )
    default_esp_proposals = ("aes256-sha1", "aes128-sha1", "3des-sha1")

    def _validate_backend(self) -> None:
        self["psk"] = self._required_string("psk")

        local_ip = self._optional_string("local_ip")
        if not local_ip:
            network = ip_network(self["pool"])
            local_ip = str(ip_address(int(network.network_address) + 1))
        else:
            try:
                local_ip = str(ip_address(local_ip))
            except ValueError as exc:
                raise ValueError("local_ip must be a valid IPv4 address") from exc

        if ":" in local_ip:
            raise ValueError("local_ip must be a valid IPv4 address")
        self["local_ip"] = local_ip

    def _metadata(self) -> dict:
        return {
            "tag": self["inbound_tag"],
            "protocol": "l2tp",
            "network": "udp",
            "tls": "none",
            "port": 500,
            "server_addr": self["server_addr"],
            "pool": self["pool"],
            "local_ip": self["local_ip"],
            "dns": list(self["dns"]),
        }
