---
title: L2TP & IKEv2 / IPsec
description: Native VPN protocols in HPXPANEL
---

# L2TP & IKEv2 / IPsec

<div class="callout-new">

This is one of HPXPANEL’s loudest upgrades: **real IPsec** in the same panel workflow as Xray users — not a bolted-on afterthought.

</div>

## What you get

| | L2TP/IPsec | IKEv2/IPsec |
| --- | --- | --- |
| Feel | Classic, widely understood | Modern, mobile-friendly |
| Typical ports | UDP `500` / `4500` / `1701` | UDP `500` / `4500` |
| Client story | Built-in VPN profiles | Native on major OS platforms |
| Panel model | Shared IPsec username/password | Same shared credentials |

Both protocols share **one IPsec username / password** pair on the user. Core editors cover server crypto, PSK, and network settings.

## When to use L2TP

- Users refuse (or cannot) install another Xray client
- You need a familiar “VPN” profile on desktop/mobile
- Compatibility matters more than bleeding-edge transport tricks

## When to use IKEv2

- Mobile networks with frequent handoffs — better reconnect behavior
- Preference for certificate-oriented IPsec setups
- Modern OS-native VPN stacks

## Operator workflow (high level)

1. Enable / configure **IPsec cores** (L2TP and/or IKEv2) in the cores UI
2. Assign protocols to users (or groups) like any other proxy
3. Deliver **connection details** + shared credentials — these are not Xray `vless://` URLs
4. Optionally still ship a subscription for the user’s proxy protocols

::: tip
The subscription page explains IPsec as connection details. Train support staff: clients need address, ports, PSK/credentials — not only a share link.
:::

## Security notes

- Prefer strong PSK and unique user passwords
- Expose only required UDP ports on the node firewall
- Pair with **IP Limiter** if accounts are redistributed

## See also

- [Protocols overview](/en/protocols/overview)
- [Users & limits](/en/users)
- [Features](/en/features)
