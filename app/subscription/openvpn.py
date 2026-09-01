import io
import zipfile

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
    def __init__(self):
        self.configs: list[tuple[str, str]] = []

    def add(self, remark: str, address: str, inbound: SubscriptionInboundData, settings: dict):
        client_cert = str(settings.get("client_cert") or "").strip()
        client_key = str(settings.get("client_key") or "").strip()
        ca_cert = str(inbound.openvpn_ca_cert or "").strip()
        if not client_cert or not client_key or not ca_cert:
            return

        lines = [
            "client",
            f"dev {inbound.openvpn_device or 'tun'}",
            f"proto {inbound.openvpn_proto or 'udp'}",
            f"remote {address} {inbound.port}",
            "resolv-retry infinite",
            "nobind",
            "persist-key",
            "persist-tun",
            "remote-cert-tls server",
            f"cipher {inbound.openvpn_cipher or 'AES-256-GCM'}",
            f"auth {inbound.openvpn_auth or 'SHA256'}",
            "verb 3",
        ]
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
        safe_name = remark.replace(" ", "_").replace("/", "_") or inbound.inbound_tag
        self.configs.append((safe_name, content))

    def render(self) -> bytes:
        if len(self.configs) == 1:
            return self.configs[0][1].encode()
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for remark, config_content in self.configs:
                zip_file.writestr(f"{remark}.ovpn", config_content)
        zip_buffer.seek(0)
        return zip_buffer.getvalue()
