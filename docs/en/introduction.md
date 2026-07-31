---
title: Introduction
description: What HPXPANEL is and why operators choose it
outline: deep
---

# Introduction

# HPXPANEL

**Command-deck proxy operations console** — a production-minded panel for users, nodes, cores, and subscriptions.

HPXPANEL is built for operators who run real fleets: hundreds of accounts, multi-node edges, and mixed cores. At the center sits **[Xray-core](https://github.com/XTLS/Xray-core)** — the industry workhorse for VMess, VLESS, Trojan, Shadowsocks, TLS, and REALITY — with **WireGuard**, **Hysteria2**, and **native IPsec (IKEv2 / L2TP)** in the same control plane.

Backend: **Python / FastAPI**. Dashboard: **React** command-deck UI.

## Why HPXPANEL?

Most panels stop at “create user → copy link.” HPXPANEL goes further:

- **Xray-first power** — VLESS / VMess / Trojan / Shadowsocks with TLS & REALITY, multi-inbound, multi-protocol users
- **Modern tunnels** — WireGuard and Hysteria2 when you need speed and different transport profiles
- **Native VPN when needed** — L2TP/IPsec & IKEv2 for stock OS clients
- **Sharp ops UI** — cobalt command-deck theme, pixel frames, readable density for long shifts
- **Abuse controls** — IP Limiter and HWID limits without babysitting every session
- **Delivery users understand** — subscription page with usage gauge, metrics, and traffic charts
- **Automation** — REST API, Telegram bot, CLI, multi-admin RBAC

## Key features

### Core capabilities

- Built-in **Web UI** with command-deck theme
- Full **REST API** backend
- **Multi-Node** infrastructure support
- **Xray protocols:** VMess, VLESS, Trojan, Shadowsocks (+ TLS / REALITY)
- **WireGuard** & **Hysteria2**
- **L2TP/IPsec** & **IKEv2/IPsec**
- Multi-protocol users, traffic & expiry limits, periodic reset strategies

### Operator extras

- Multi-step **create-user wizard**
- **IP Limiter** (max concurrent unique IPs)
- Subscription links for V2Ray / Clash / ClashMeta
- QR codes, Telegram bot, CLI
- Flexible **Xray core** editors, multi-language dashboard

## Quick start

1. Install on a Linux server — see [Installation](/en/installation)
2. Generate an owner temp key with the CLI
3. Open the dashboard and create your owner account
4. Configure Xray cores — see [Xray stack](/en/protocols/xray)
5. Optionally enable native VPN — see [L2TP & IKEv2](/en/protocols/ipsec)

## Community & support

- **GitHub:** [pooyahpx/HPXPANEL](https://github.com/pooyahpx/HPXPANEL)
- **dev by hpx:** [github.com/pooyahpx](https://github.com/pooyahpx)

---

Ready? Jump to the [Linux install guide](/en/installation).
