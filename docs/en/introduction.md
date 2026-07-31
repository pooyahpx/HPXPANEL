---
title: Introduction
description: What HPXPANEL is and why operators choose it
outline: deep
---

# Introduction

# HPXPANEL

**Command-deck proxy operations console** — a production-minded panel for users, nodes, cores, and subscriptions.

HPXPANEL is built for operators who run real fleets: hundreds of accounts, multi-node edges, mixed cores, and clients that need **native OS VPN** — not only Xray share links. Backend on **Python / FastAPI**, dashboard on **React**, engines on **Xray-core**, **WireGuard**, and **IPsec (IKEv2 / L2TP)**.

## Why HPXPANEL?

Most panels stop at “create user → copy link.” HPXPANEL goes further:

- **Native VPN stack** — L2TP/IPsec and IKEv2 wired into the same user/core workflow
- **Sharp ops UI** — cobalt command-deck theme, pixel frames, readable density for long shifts
- **Abuse controls** — IP Limiter and HWID limits without babysitting every session
- **Delivery that users understand** — subscription page with usage gauge, metrics, and traffic charts
- **Automation** — REST API, Telegram bot, CLI, multi-admin RBAC

## Key features

### Core capabilities

- Built-in **Web UI** with command-deck theme
- Full **REST API** backend
- **Multi-Node** infrastructure support
- Protocols: VMess, VLESS, Trojan, Shadowsocks, WireGuard, Hysteria2
- **L2TP/IPsec** and **IKEv2/IPsec**
- Multi-protocol users, traffic & expiry limits, periodic reset strategies

### Operator extras

- Multi-step **create-user wizard**
- **IP Limiter** (max concurrent unique IPs)
- Subscription links for V2Ray / Clash / ClashMeta
- QR codes, Telegram bot, CLI
- TLS & REALITY, multi-language dashboard

## Quick start

1. Install on a Linux server — see [Installation](/en/installation)
2. Generate an owner temp key with the CLI
3. Open the dashboard and create your owner account
4. Configure cores (including IPsec) — see [L2TP & IKEv2](/en/protocols/ipsec)

## Community & support

- **GitHub:** [pooyahpx/HPXPANEL](https://github.com/pooyahpx/HPXPANEL)
- **dev by hpx:** [github.com/pooyahpx](https://github.com/pooyahpx)

---

Ready? Jump to the [Linux install guide](/en/installation).
