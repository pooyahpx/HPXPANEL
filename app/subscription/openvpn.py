from app.models.subscription import SubscriptionInboundData

from .base import BaseSubscription


def _pem_block(tag: str, content: str) -> str:
    body = content.strip()
    if not body:
        return ""
    if f"<{tag}>" in body:
        return body
    return f"<{tag}>\n{body}\n</{tag}>\n"


class OpenVPNConfiguration(BaseSubscription):
    """Build a single inline .ovpn profile (OpenVPN Connect rejects zip/binary)."""

    def __init__(self):
        self._remotes: list[tuple[str, int]] = []
        self._inbound: SubscriptionInboundData | None = None
        self._settings: dict | None = None

    def add(self, remark: str, address: str, inbound: SubscriptionInboundData, settings: dict):
        client_cert = str(settings.get("client_cert") or "").strip()
        client_key = str(settings.get("client_key") or "").strip()
        ca_cert = str(inbound.openvpn_ca_cert or "").strip()
        host = str(address or "").strip()
        if not client_cert or not client_key or not ca_cert or not host:
            return

        if self._inbound is None:
            self._inbound = inbound
            self._settings = {"client_cert": client_cert, "client_key": client_key}

        remote = (host, inbound.port)
        if remote not in self._remotes:
            self._remotes.append(remote)

    def render(self) -> bytes:
        if not self._inbound or not self._settings or not self._remotes:
            return b""

        inbound = self._inbound
        client_cert = self._settings["client_cert"]
        client_key = self._settings["client_key"]
        ca_cert = str(inbound.openvpn_ca_cert or "").strip()

        lines = [
            "client",
            f"dev {inbound.openvpn_device or 'tun'}",
            f"proto {inbound.openvpn_proto or 'udp'}",
        ]
        for address, port in self._remotes:
            lines.append(f"remote {address} {port}")
        lines.extend(
            [
                "resolv-retry infinite",
                "nobind",
                "persist-key",
                "persist-tun",
                "remote-cert-tls server",
                f"cipher {inbound.openvpn_cipher or 'AES-256-GCM'}",
                f"auth {inbound.openvpn_auth or 'SHA256'}",
                "verb 3",
            ]
        )
        if inbound.openvpn_dns:
            lines.append(f"dhcp-option DNS {inbound.openvpn_dns[0]}")

        blocks = [
            "\n".join(lines),
            _pem_block("ca", ca_cert),
            _pem_block("cert", client_cert),
            _pem_block("key", client_key),
        ]
        tls_crypt = str(inbound.openvpn_tls_crypt_key or "").strip()
        if tls_crypt:
            blocks.append(_pem_block("tls-crypt", tls_crypt))

        content = "\n".join(block for block in blocks if block).strip() + "\n"
        return content.encode()
