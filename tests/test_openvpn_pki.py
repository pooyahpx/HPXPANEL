from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

from app.utils.openvpn_pki import generate_openvpn_pki, generate_tls_crypt_key


def test_generate_tls_crypt_key_format():
    key = generate_tls_crypt_key()
    assert key.startswith("-----BEGIN OpenVPN Static key V1-----")
    assert key.strip().endswith("-----END OpenVPN Static key V1-----")


def test_generate_openvpn_pki_produces_valid_pem_chain():
    bundle = generate_openvpn_pki()

    assert bundle["ca_cert"].startswith("-----BEGIN CERTIFICATE-----")
    assert bundle["server_cert"].startswith("-----BEGIN CERTIFICATE-----")
    assert bundle["server_key"].startswith("-----BEGIN")
    assert bundle["tls_crypt_key"].startswith("-----BEGIN OpenVPN Static key V1-----")

    ca = x509.load_pem_x509_certificate(bundle["ca_cert"].encode(), default_backend())
    server = x509.load_pem_x509_certificate(bundle["server_cert"].encode(), default_backend())
    assert server.issuer == ca.subject

    private_key = serialization.load_pem_private_key(bundle["server_key"].encode(), password=None)
    assert private_key.public_key().public_numbers() == server.public_key().public_numbers()
