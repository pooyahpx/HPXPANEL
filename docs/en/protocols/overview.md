---
title: Protocols overview
description: Xray, WireGuard, Hysteria2, and native IPsec in HPXPANEL
---

# Protocols overview

HPXPANEL is **Xray-first**, then expands into modern tunnels and native OS VPN — all from one panel.

## Xray family (main stack)

Powered by **[Xray-core](https://github.com/XTLS/Xray-core)** — the backbone of most serious proxy fleets.

| Protocol | Why operators love it |
| --- | --- |
| **VLESS** | Lightweight, flexible, pairs beautifully with REALITY / TLS |
| **VMess** | Classic Xray family — huge client ecosystem |
| **Trojan** | TLS-shaped traffic that blends into normal HTTPS |
| **Shadowsocks** | Simple, battle-tested, broad client support |

**Security layers:** TLS · **REALITY** · multi-inbound / multi-protocol per user

→ Deep dive: [Xray stack](/en/protocols/xray)

## Modern tunnels

| Protocol | Why it matters |
| --- | --- |
| **WireGuard** | Clean crypto, low overhead, excellent throughput |
| **Hysteria2** | Aggressive performance on lossy / high-latency paths |

## Native VPN (IPsec)

| Protocol | Ports (typical) | Auth model |
| --- | --- | --- |
| L2TP/IPsec | UDP `500`, `4500`, `1701` | PSK + shared username/password |
| IKEv2/IPsec | UDP `500`, `4500` | Certificate-friendly + shared credentials |

→ [L2TP & IKEv2 / IPsec](/en/protocols/ipsec)

## How to pick

| Need | Reach for |
| --- | --- |
| Censorship resistance, flexible clients, REALITY | **Xray** (VLESS / VMess / Trojan / SS) |
| Raw speed / simple modern VPN | **WireGuard** |
| Harsh networks, UDP-oriented speed | **Hysteria2** |
| Stock OS VPN settings, no extra app | **L2TP / IKEv2** |

You can mix them on one user — that’s the point of a multi-protocol panel.
