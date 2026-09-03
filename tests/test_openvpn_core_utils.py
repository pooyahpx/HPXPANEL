from app.utils.openvpn_core import openvpn_ca_key_missing, openvpn_pki_ready


def test_openvpn_pki_ready_requires_ca_key():
    assert openvpn_pki_ready(
        {
            "ca_cert": "-----BEGIN CERTIFICATE-----\nabc\n-----END CERTIFICATE-----",
            "ca_key": "-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----",
            "server_cert": "-----BEGIN CERTIFICATE-----\ndef\n-----END CERTIFICATE-----",
            "server_key": "-----BEGIN PRIVATE KEY-----\ndef\n-----END PRIVATE KEY-----",
        }
    )


def test_openvpn_ca_key_missing_when_cert_without_key():
    config = {
        "ca_cert": "-----BEGIN CERTIFICATE-----\nabc\n-----END CERTIFICATE-----",
        "server_cert": "x",
        "server_key": "y",
    }
    assert openvpn_ca_key_missing(config) is True
    assert openvpn_pki_ready(config) is False
