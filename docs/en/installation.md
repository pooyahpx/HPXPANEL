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
sudo bash -c "$(curl -fsSL https://github.com/pooyahpx/HPXPANEL/raw/main/scripts/hpxpanel.sh)" @ install --database timescaledb
```

```bash [SQLite]
sudo bash -c "$(curl -fsSL https://github.com/pooyahpx/HPXPANEL/raw/main/scripts/hpxpanel.sh)" @ install
```

```bash [MySQL]
sudo bash -c "$(curl -fsSL https://github.com/pooyahpx/HPXPANEL/raw/main/scripts/hpxpanel.sh)" @ install --database mysql
```

```bash [MariaDB]
sudo bash -c "$(curl -fsSL https://github.com/pooyahpx/HPXPANEL/raw/main/scripts/hpxpanel.sh)" @ install --database mariadb
```

```bash [PostgreSQL]
sudo bash -c "$(curl -fsSL https://github.com/pooyahpx/HPXPANEL/raw/main/scripts/hpxpanel.sh)" @ install --database postgresql
```

:::

::: tip Recommended
**TimescaleDB** is preferred for metrics-heavy deployments.
:::

## After install

| Path | Purpose |
| --- | --- |
| `/opt/hpxpanel` | Application files |
| `/opt/hpxpanel/.env` | Configuration |
| `/var/lib/hpxpanel` | Persistent data |
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
hpxpanel cli forge-seal
hpxpanel --help
```

Use the one-time key on the dashboard login page to create the owner account.

## Install an HPX node

On each edge server (Linux), run the HPX node installer. It deploys a Docker node with **Xray**, **WireGuard**, **OpenVPN**, and **IKEv2 / IPsec**, then prints the values you paste into **HPXPANEL → Nodes**.

```bash
sudo bash -c "$(curl -fsSL https://github.com/pooyahpx/HPXNODE/raw/main/scripts/install.sh)" @ install
```

Non-interactive example:

```bash
sudo bash -c "$(curl -fsSL https://github.com/pooyahpx/HPXNODE/raw/main/scripts/install.sh)" @ install -y \
  --service-port 62050 \
  --disable openvpn
```

After install, register the node in the panel with the same **Address**, **Node Port**, **API key**, and **Server CA**.

| Path | Purpose |
| --- | --- |
| `/opt/hpx-node` | Compose + installer copy |
| `/var/lib/hpx-node` | Certs + generated configs |
| `hpx-node status` / `logs` / `update` | Manage the node |

## Common `hpxpanel` commands

| Command | Purpose |
| --- | --- |
| `hpxpanel status` | Container status |
| `hpxpanel restart -n` | Restart without pulling |
| `hpxpanel update` | Update image + scripts |
| `hpxpanel install-script` | Refresh CLI scripts from git only |
| `hpxpanel edit-env` / edit `/opt/hpxpanel/.env` | Configuration |
| `hpxpanel ssl --domain panel.example.com` | Let's Encrypt certificate |
| `hpxpanel backup` | Full CLI backup (includes `.env`) |
| `hpxpanel restore` | Restore from zip (CLI or Settings→Backup archives) |
| `hpxpanel logs` | Service logs |
| `hpxpanel cli …` | In-container app CLI |

## Public URL and Pulse / Abroad

The panel container often listens on `UVICORN_PORT=8000`. If you expose it on **443** (nginx/caddy), set in `.env` **without** `:8000`:

```bash
PANEL_PUBLIC_URL=https://panel.example.com
```

Newer builds prefer the browser URL for join commands and strip internal `:8000` from public HTTPS URLs. After changing `.env`:

```bash
hpxpanel restart -n
```

Then regenerate **Tokens** in **HPX Pulse**.

Test from the Abroad VPS:

```bash
curl -I --connect-timeout 10 https://panel.example.com/
```

## Backup and restore

### Dashboard one-click

1. Set `BACKUP_ALLOW_PANEL_RESTORE=true` in `/opt/hpxpanel/.env`
2. `hpxpanel restart -n`
3. **Settings → Backup** → Import or Backup now → Restore

The panel restores the **local** zip (it never contacts an old server), starts TimescaleDB/Postgres via Docker when needed, and uses the TimescaleDB-safe path — no manual SSH for `docker compose up` / `hpxpanel restore`.

### CLI

```bash
hpxpanel install-script
hpxpanel restore
# or:
hpxpanel restore --file /var/lib/hpxpanel/backups/hpxpanel_YYYYMMDD_HHMMSS.zip --yes
```

## Next

- [Install from source](/en/source) — develop against this repository
- [L2TP & IKEv2 / IPsec](/en/protocols/ipsec) — enable native VPN protocols
- [Users & limits](/en/users) — wizard, IP Limiter, HWID
