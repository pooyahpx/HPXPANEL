from app.core.credential_vpn import CredentialVpnConfig
from app.db.models import CoreType
from app.models.protocol import ProxyProtocol


class SSTPConfig(CredentialVpnConfig):
    core_type = CoreType.sstp
    protocol = ProxyProtocol.sstp
    default_port = 443
    network = "tcp"

    def _validate_backend(self) -> None:
        if not self["server_addr"]:
            raise ValueError("server_addr is required")
