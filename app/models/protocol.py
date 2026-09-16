from enum import IntEnum


class ProxyProtocol(IntEnum):
    vmess = 1
    vless = 2
    trojan = 3
    shadowsocks = 4
    wireguard = 5
    hysteria = 6
    ikev2 = 7
    l2tp = 8
    openvpn = 9
    anytls = 10
    tuic = 11
    naive = 12
    pptp = 13
    openconnect = 14
    sstp = 15
    wg_c = 16
    amneziawg = 17
    gre = 18
    ssh = 19
    mtproto = 20

    @classmethod
    def from_value(cls, value: str) -> ProxyProtocol | None:
        try:
            return _PROXY_PROTOCOL_BY_NAME[value]
        except KeyError:
            return None


_PROXY_PROTOCOL_BY_NAME = {protocol.name: protocol for protocol in ProxyProtocol}
