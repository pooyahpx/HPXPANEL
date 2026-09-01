from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID


def _pem_private_key(key: rsa.RSAPrivateKey) -> str:
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()


def _pem_certificate(cert: x509.Certificate) -> str:
    return cert.public_bytes(serialization.Encoding.PEM).decode()


def generate_tls_crypt_key() -> str:
    key_bytes = os.urandom(256)
    hex_lines = [key_bytes[index : index + 16].hex() for index in range(0, 256, 16)]
    body = "\n".join(hex_lines)
    return f"-----BEGIN OpenVPN Static key V1-----\n{body}\n-----END OpenVPN Static key V1-----\n"


def generate_openvpn_pki(
    *,
    ca_common_name: str = "HPXPANEL-OpenVPN-CA",
    server_common_name: str = "openvpn-server",
    valid_days: int = 3650,
) -> dict[str, str]:
    """Generate a fresh OpenVPN CA, server certificate, server key, and TLS-Crypt key."""
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, ca_common_name)])
    now = datetime.now(UTC)
    expires = now + timedelta(days=valid_days)

    ca_cert = (
        x509.CertificateBuilder()
        .subject_name(ca_name)
        .issuer_name(ca_name)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(expires)
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_cert_sign=True,
                crl_sign=True,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .sign(ca_key, hashes.SHA256())
    )

    server_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    server_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, server_common_name)])

    server_cert = (
        x509.CertificateBuilder()
        .subject_name(server_name)
        .issuer_name(ca_name)
        .public_key(server_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(expires)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=True,
                content_commitment=False,
                data_encipherment=False,
                key_cert_sign=False,
                crl_sign=False,
                key_agreement=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
        .sign(ca_key, hashes.SHA256())
    )

    return {
        "ca_cert": _pem_certificate(ca_cert),
        "ca_key": _pem_private_key(ca_key),
        "server_cert": _pem_certificate(server_cert),
        "server_key": _pem_private_key(server_key),
        "tls_crypt_key": generate_tls_crypt_key(),
    }


def sign_client_certificate(
    *,
    ca_key_pem: str,
    ca_cert_pem: str,
    common_name: str,
    valid_days: int = 3650,
) -> tuple[str, str]:
    ca_key = serialization.load_pem_private_key(ca_key_pem.encode(), password=None)
    ca_cert = x509.load_pem_x509_certificate(ca_cert_pem.encode())
    client_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
    now = datetime.now(UTC)
    expires = now + timedelta(days=valid_days)

    client_cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca_cert.subject)
        .public_key(client_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(expires)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=True,
                content_commitment=False,
                data_encipherment=False,
                key_cert_sign=False,
                crl_sign=False,
                key_agreement=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.CLIENT_AUTH]), critical=False)
        .sign(ca_key, hashes.SHA256())
    )
    return _pem_certificate(client_cert), _pem_private_key(client_key)


def cert_serial_hex(client_cert_pem: str) -> str:
    cert = x509.load_pem_x509_certificate(client_cert_pem.encode())
    return format(cert.serial_number, "x")


def cert_fingerprint_sha256(client_cert_pem: str) -> str:
    cert = x509.load_pem_x509_certificate(client_cert_pem.encode())
    digest = cert.fingerprint(hashes.SHA256()).hex()
    return f"sha256:{digest}"
