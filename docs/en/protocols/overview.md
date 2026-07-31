---
title: Protocols overview
description: Proxy and native VPN protocols supported by HPXPANEL
---

# Protocols overview

HPXPANEL spans two worlds: **proxy/tunnel apps** and **native OS VPN**.

## Proxy / advanced tunnels

| Protocol | Notes |
| --- | --- |
| VMess | Classic Xray family |
| VLESS | Lightweight Xray |
| Trojan | TLS-friendly |
| Shadowsocks | Broad client support |
| WireGuard | Fast modern VPN |
| Hysteria2 | High-performance UDP-oriented |

Plus **TLS** and **REALITY** where the core supports them.

## Native VPN (IPsec)

| Protocol | Ports (typical) | Auth model |
| --- | --- | --- |
| **L2TP/IPsec** | UDP `500`, `4500`, `1701` | PSK + shared username/password |
| **IKEv2/IPsec** | UDP `500`, `4500` | Certificate-friendly + shared credentials |

→ Full guide: [L2TP & IKEv2 / IPsec](/en/protocols/ipsec)

## Why both?

Proxy stacks win on flexibility and censorship resistance.  
Native IPsec wins when the client must use **built-in VPN settings** on Windows / iOS / Android / macOS — “just Connect.”
