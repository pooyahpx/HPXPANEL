from app.core.credential_vpn import CredentialVpnConfig
from app.db.models import CoreType
from app.models.protocol import ProxyProtocol


class PPTPConfig(CredentialVpnConfig):
    core_type = CoreType.pptp
    protocol = ProxyProtocol.pptp
    default_port = 1723
    network = "tcp"
