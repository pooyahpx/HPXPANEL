from app.core.credential_vpn import CredentialVpnConfig
from app.db.models import CoreType
from app.models.protocol import ProxyProtocol


class SSHConfig(CredentialVpnConfig):
    core_type = CoreType.ssh
    protocol = ProxyProtocol.ssh
    default_port = 22
    network = "tcp"
    require_pool = False

    def _validate_backend(self) -> None:
        if not self["server_addr"]:
            raise ValueError("server_addr is required")
        banner = self._optional_string("banner")
        if banner:
            self["banner"] = banner
