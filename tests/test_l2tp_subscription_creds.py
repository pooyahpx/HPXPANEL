"""L2TP subscription must reuse IKEv2 credentials (ProxyTable has no l2tp key)."""

import pytest

from app.models.subscription import SubscriptionInboundData, TCPTransportConfig, TLSConfig
from app.subscription.links import StandardLinks
from app.subscription.share import process_host


def _l2tp_inbound(*, psk: str = "", port: list[int] | int = (500,)) -> SubscriptionInboundData:
    return SubscriptionInboundData(
        remark="L2TP",
        inbound_tag="l2tp-main",
        protocol="l2tp",
        address="203.0.113.50",
        port=list(port) if isinstance(port, tuple) else port,
        network="udp",
        tls_config=TLSConfig(tls="none", sni=[]),
        transport_config=TCPTransportConfig(path="", host=[]),
        l2tp_psk=psk,
    )


@pytest.mark.asyncio
async def test_process_host_l2tp_uses_ikev2_credentials():
    inbound, settings = await process_host(
        _l2tp_inbound(),
        format_variables={},
        inbounds=["l2tp-main"],
        proxies={"ikev2": {"username": "alice", "password": "s3cret"}},
    )
    assert inbound.protocol == "l2tp"
    assert settings["username"] == "alice"
    assert settings["password"] == "s3cret"


@pytest.mark.asyncio
async def test_process_host_l2tp_ignores_empty_l2tp_key():
    """Even a truthy empty-username l2tp bag must not win over ikev2."""
    _, settings = await process_host(
        _l2tp_inbound(),
        format_variables={},
        inbounds=["l2tp-main"],
        proxies={
            "l2tp": {"username": "", "password": "wrong"},
            "ikev2": {"username": "alice", "password": "s3cret"},
        },
    )
    assert settings["username"] == "alice"
    assert settings["password"] == "s3cret"


@pytest.mark.asyncio
async def test_process_host_l2tp_missing_credentials_returns_none():
    result = await process_host(
        _l2tp_inbound(),
        format_variables={},
        inbounds=["l2tp-main"],
        proxies={"vmess": {"id": "x"}},
    )
    assert result is None


def test_l2tp_link_includes_psk():
    links = StandardLinks()
    uri = links._build_credential_vpn(
        "L2TP",
        "203.0.113.50",
        _l2tp_inbound(psk="shared-secret", port=500),
        {"username": "alice", "password": "s3cret"},
    )
    assert uri.startswith("l2tp://alice:s3cret@203.0.113.50:500?")
    assert "psk=shared-secret" in uri
    assert uri.endswith("#L2TP")


def test_l2tp_link_skips_blank_credentials():
    links = StandardLinks()
    assert (
        links._build_credential_vpn(
            "L2TP",
            "203.0.113.50",
            _l2tp_inbound(port=500),
            {"username": "", "password": "x"},
        )
        == ""
    )
