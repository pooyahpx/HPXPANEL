---
title: Installation
description: Install HPXPANEL on Linux with one-liner scripts
---

# Installation

> Quick start — bring the panel up on a Linux server in minutes.

## Requirements

- Linux (Ubuntu / Debian recommended)
- `sudo` access
- A domain for production SSL

## One-line install

Pick a database:

::: code-group

```bash [TimescaleDB]
sudo bash -c "$(curl -fsSL https://github.com/PasarGuard/scripts/raw/main/pasarguard.sh)" @ install --database timescaledb
```

```bash [SQLite]
sudo bash -c "$(curl -fsSL https://github.com/PasarGuard/scripts/raw/main/pasarguard.sh)" @ install
```

```bash [MySQL]
sudo bash -c "$(curl -fsSL https://github.com/PasarGuard/scripts/raw/main/pasarguard.sh)" @ install --database mysql
```

```bash [MariaDB]
sudo bash -c "$(curl -fsSL https://github.com/PasarGuard/scripts/raw/main/pasarguard.sh)" @ install --database mariadb
```

```bash [PostgreSQL]
sudo bash -c "$(curl -fsSL https://github.com/PasarGuard/scripts/raw/main/pasarguard.sh)" @ install --database postgresql
```

:::

::: tip Recommended
**TimescaleDB** is preferred for metrics-heavy deployments.
:::

## After install

| Path | Purpose |
| --- | --- |
| `/opt/pasarguard` | Application files |
| `/opt/pasarguard/.env` | Configuration |
| `/var/lib/pasarguard` | Persistent data |
| `https://YOUR_DOMAIN:8000/dashboard/` | Production dashboard |

::: warning SSL required
Production dashboards expect TLS. Issue a certificate for your domain before going live.
:::

## Test without a domain

SSH port forwarding:

```bash
ssh -L 8000:localhost:8000 user@serverip
```

Then open `http://localhost:8000/dashboard/`.

::: danger Testing only
Closing the SSH session drops access.
:::

## Bootstrap owner

```bash
pasarguard cli generate-temp-key
pasarguard --help
```

Use the one-time key on the dashboard login page to create the owner account.

## Next

- [Install from source](/en/source) — develop against this repository
- [L2TP & IKEv2 / IPsec](/en/protocols/ipsec) — enable native VPN protocols
- [Users & limits](/en/users) — wizard, IP Limiter, HWID
