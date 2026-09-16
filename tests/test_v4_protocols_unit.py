import pytest

from app.core.amneziawg import AmneziaWGConfig
from app.core.gre import GREConfig
from app.core.mtproto import MtprotoConfig
from app.core.openconnect import OpenConnectConfig
from app.core.pptp import PPTPConfig
from app.core.ssh import SSHConfig
from app.core.sstp import SSTPConfig
from app.core.wg_c import WireGuardCConfig
from app.core.xray import XRayConfig
from app.db.models import CoreType
from app.models.protocol import ProxyProtocol
from app.models.proxy import ProxyTable
from app.utils.crypto import generate_wireguard_keypair


def _wg_base(**extra):
    private_key, _ = generate_wireguard_keypair()
    cfg = {
        "interface_name": "wg0",
        "private_key": private_key,
        "listen_port": 51820,
        "address": ["10.66.0.1/24"],
        "dns": ["1.1.1.1"],
    }
    cfg.update(extra)
    return cfg


def test_pptp_config_ok():
    cfg = PPTPConfig({"inbound_tag": "pptp", "port": 1723, "pool": "10.30.0.0/24", "dns": ["1.1.1.1"]})
    assert cfg.type == CoreType.pptp
    assert cfg.protocols == frozenset((ProxyProtocol.pptp,))
    assert "pptp" in cfg.inbounds


def test_openconnect_requires_server_addr():
    with pytest.raises(ValueError, match="server_addr"):
        OpenConnectConfig({"inbound_tag": "oc", "port": 443, "pool": "10.31.0.0/24"})


def test_sstp_and_ssh_ok():
    sstp = SSTPConfig({"inbound_tag": "sstp", "server_addr": "1.2.3.4", "port": 443, "pool": "10.32.0.0/24"})
    assert sstp.type == CoreType.sstp
    ssh = SSHConfig({"inbound_tag": "ssh", "server_addr": "1.2.3.4", "port": 22})
    assert ssh.type == CoreType.ssh
    assert "pool" not in ssh


def test_gre_requires_peer():
    with pytest.raises(ValueError, match="peer_addr"):
        GREConfig({"inbound_tag": "gre", "server_addr": "1.2.3.4", "port": 0, "pool": "10.33.0.0/24"})
    gre = GREConfig(
        {
            "inbound_tag": "gre",
            "server_addr": "1.2.3.4",
            "port": 0,
            "pool": "10.33.0.0/24",
            "peer_addr": "5.6.7.8",
            "ipsec": True,
        }
    )
    assert gre["peer_addr"] == "5.6.7.8"
    assert gre.inbounds_by_tag["gre"]["protocol"] == "gre"


def test_mtproto_secret_length():
    with pytest.raises(ValueError, match="secret"):
        MtprotoConfig({"inbound_tag": "mt", "server_addr": "1.2.3.4", "port": 443, "secret": "short"})
    mt = MtprotoConfig(
        {"inbound_tag": "mt", "server_addr": "1.2.3.4", "port": 443, "secret": "0123456789abcdef", "mode": "dd"}
    )
    assert mt.type == CoreType.mtproto


def test_wg_c_and_amnezia():
    wgc = WireGuardCConfig(_wg_base())
    assert wgc.type == CoreType.wg_c
    assert wgc.inbounds_by_tag["wg0"]["protocol"] == "wg_c"
    awg = AmneziaWGConfig(_wg_base(jc=5, jmin=10, jmax=20))
    assert awg.type == CoreType.amneziawg
    assert awg["jc"] == 5
    with pytest.raises(ValueError, match="jmin"):
        AmneziaWGConfig(_wg_base(jc=4, jmin=80, jmax=10))


def test_xray_accepts_anytls_tuic_naive():
    base = {
        "log": {"loglevel": "warning"},
        "inbounds": [
            {
                "tag": "anytls-in",
                "protocol": "anytls",
                "port": 443,
                "settings": {"clients": []},
                "streamSettings": {"network": "tcp", "security": "tls", "tlsSettings": {"certificates": []}},
            },
            {
                "tag": "tuic-in",
                "protocol": "tuic",
                "port": 8443,
                "settings": {"clients": []},
                "streamSettings": {"network": "tcp", "security": "tls", "tlsSettings": {"certificates": []}},
            },
            {
                "tag": "naive-in",
                "protocol": "naive",
                "port": 8444,
                "settings": {"clients": []},
                "streamSettings": {"network": "tcp", "security": "tls", "tlsSettings": {"certificates": []}},
            },
        ],
        "outbounds": [{"protocol": "freedom", "tag": "direct"}],
    }
    cfg = XRayConfig(base)
    assert ProxyProtocol.anytls in cfg.protocols
    assert ProxyProtocol.tuic in cfg.protocols
    assert ProxyProtocol.naive in cfg.protocols


def test_proxy_table_includes_new_protocols():
    table = ProxyTable()
    dumped = table.dict()
    for key in (
        "anytls",
        "tuic",
        "naive",
        "pptp",
        "openconnect",
        "sstp",
        "ssh",
        "wg_c",
        "amneziawg",
        "gre",
        "mtproto",
    ):
        assert key in dumped


def test_backend_type_for_core_new_types_message():
    from types import SimpleNamespace

    from app.operation import node as node_op

    class FakeBackend:
        XRAY = 1
        WIREGUARD = 2
        IKEV2 = 3
        L2TP = 4
        OPENVPN = 5

    fake_service = SimpleNamespace(BackendType=FakeBackend)
    original = node_op.service
    node_op.service = fake_service
    try:
        with pytest.raises(RuntimeError, match="PPTP"):
            node_op._backend_type_for_core(CoreType.pptp)
        with pytest.raises(RuntimeError, match="AMNEZIAWG"):
            node_op._backend_type_for_core(CoreType.amneziawg)
    finally:
        node_op.service = original
