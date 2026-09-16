from app.models.subscription import SubscriptionInboundData, TCPTransportConfig, TLSConfig
from app.subscription.links import StandardLinks


def _inbound(protocol: str, port: int = 443) -> SubscriptionInboundData:
    return SubscriptionInboundData(
        remark="r",
        inbound_tag=f"{protocol}-tag",
        protocol=protocol,
        address="203.0.113.10",
        port=port,
        network="tcp",
        tls_config=TLSConfig(tls="tls", sni=["example.com"]),
        transport_config=TCPTransportConfig(path="", host=[]),
    )


def test_anytls_tuic_naive_links():
    links = StandardLinks()
    links.add("Any", "203.0.113.10", _inbound("anytls"), {"password": "secret"})
    links.add("Tuic", "203.0.113.10", _inbound("tuic", 8443), {"id": "11111111-1111-1111-1111-111111111111", "password": "pw"})
    links.add("Naive", "203.0.113.10", _inbound("naive"), {"username": "u", "password": "p"})
    rendered = links.render()
    assert "anytls://" in rendered
    assert "tuic://" in rendered
    assert "naive+https://" in rendered


def test_credential_and_mtproto_links():
    links = StandardLinks()
    links.add("PPTP", "203.0.113.10", _inbound("pptp", 1723), {"username": "u", "password": "p"})
    links.add("MT", "203.0.113.10", _inbound("mtproto"), {"secret": "0123456789abcdef"})
    rendered = links.render()
    assert "pptp://u:p@203.0.113.10:1723" in rendered
    assert "tg://proxy?server=203.0.113.10" in rendered
