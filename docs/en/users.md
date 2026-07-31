---
title: Users & limits
description: Create-user wizard, traffic limits, IP Limiter, HWID
---

# Users & limits

## Create-user wizard

HPXPANEL uses a multi-step flow instead of one oversized form:

1. **Identity** — username and basics
2. **Access** — protocols / proxies / groups
3. **Limits** — traffic, expiry, reset strategy, **IP Limiter**, HWID
4. **Advanced** — extras when you need them

A live draft rail keeps the operator oriented while stepping through.

## Traffic & expiry

- Absolute traffic caps
- Expiry dates
- Periodic reset strategies (daily, weekly, …)

## IP Limiter

Set a maximum number of **concurrent unique client IPs** per user.

Use it when:

- accounts are shared beyond your plan
- you want soft abuse control without killing legitimate multi-device use entirely

## HWID limit

Hardware-based device caps for clients that report HWID.

## Multi-protocol users

One user can carry multiple protocols — including proxy protocols **and** IPsec credentials for L2TP / IKEv2 when enabled on cores.
