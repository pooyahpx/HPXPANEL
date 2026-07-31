---
title: Xray stack
description: VMess, VLESS, Trojan, Shadowsocks, TLS and REALITY in HPXPANEL
---

# Xray stack

<div class="callout-new">

**Xray-core is the heart of HPXPANEL.** Most of your fleet will live here — flexible protocols, REALITY / TLS, multi-inbound workflows, and subscription delivery that every client already understands.

</div>

HPXPANEL manages [Xray-core](https://github.com/XTLS/Xray-core) through dedicated **core editors**, hosts, inbounds, and per-user proxy settings — without forcing you to hand-edit production JSON every night.

## Protocols

### VLESS

The modern lightweight Xray protocol. Minimal overhead, excellent with **REALITY** and TLS, and the default choice for many high-resistance deployments.

### VMess

The classic. Massive client support, mature tooling, still a workhorse when you need wide compatibility across older and newer apps.

### Trojan

Looks like normal HTTPS. Great when you want traffic that blends into TLS-looking sessions while staying inside the Xray ecosystem.

### Shadowsocks

Simple, proven, everywhere. Ideal for clients and networks that expect SS — still first-class in HPXPANEL, not an afterthought.

## Security & transport

| Layer | Role |
| --- | --- |
| **TLS** | Standard encrypted transport |
| **REALITY** | Advanced anti-detection / camouflage for hostile networks |
| Multi-inbound | Several listeners / fallbacks on smart port layouts |
| Multi-protocol users | One account, many Xray protocols at once |

## Operator workflow

1. Create / edit an **Xray core** in the cores UI
2. Attach **hosts / inbounds** for the node
3. Enable the protocols on the user (wizard: Access step)
4. Ship a **subscription** — V2Ray / Clash / ClashMeta clients just work
5. Watch usage on the subscription page + panel statistics

## Why Xray still wins daily

- Deep client ecosystem (v2rayN, Streisand, Hiddify, ClashMeta, …)
- REALITY + VLESS is still one of the strongest practical stacks under censorship
- One core can serve many users and protocols efficiently
- Subscriptions + QR make support tickets shorter

## Pair with the rest of the panel

- Add **WireGuard / Hysteria2** for users who need a different tunnel profile
- Add **L2TP / IKEv2** when someone can only use built-in OS VPN
- Lock abuse with **IP Limiter** and **HWID**

## See also

- [Protocols overview](/en/protocols/overview)
- [Subscriptions](/en/subscriptions)
- [L2TP & IKEv2 / IPsec](/en/protocols/ipsec)
- [Users & limits](/en/users)
