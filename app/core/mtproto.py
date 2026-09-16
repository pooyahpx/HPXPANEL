from app.core.credential_vpn import CredentialVpnConfig
from app.db.models import CoreType
from app.models.protocol import ProxyProtocol


class MtprotoConfig(CredentialVpnConfig):
    core_type = CoreType.mtproto
    protocol = ProxyProtocol.mtproto
    default_port = 443
    network = "tcp"
    require_pool = False

    def _validate_backend(self) -> None:
        if not self["server_addr"]:
            raise ValueError("server_addr is required")
        secret = self._required_string("secret")
        if len(secret) < 16:
            raise ValueError("secret must be at least 16 characters")
        self["secret"] = secret
        mode = (self._optional_string("mode") or "dd").lower()
        if mode not in {"dd", "tls", "fake-tls", "simple"}:
            raise ValueError("mode must be one of: dd, tls, fake-tls, simple")
        self["mode"] = mode

    def _metadata(self) -> dict:
        meta = super()._metadata()
        meta.update({"mode": self["mode"], "secret": self["secret"]})
        return meta
