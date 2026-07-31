<p align="center">
  <img width="96" height="96" alt="HPXPANEL" src="https://raw.githubusercontent.com/pooyahpx/HPXPANEL/main/dashboard/public/statics/favicon/android-chrome-192x192.png">
</p>

<h1 align="center">HPXPANEL</h1>

<p align="center">
  <b>The ops console that treats proxies like infrastructure — not a spreadsheet.</b>
</p>

<p align="center">
  <a href="./README.md">English</a> ·
  <a href="./README-fa.md">فارسی</a> ·
  <a href="./README-ru.md">Русский</a>
</p>

<p align="center">
  <img alt="build" src="https://img.shields.io/github/actions/workflow/status/pooyahpx/HPXPANEL/build.yml?style=flat-square&label=build">
  <img alt="license" src="https://img.shields.io/github/license/pooyahpx/HPXPANEL?style=flat-square">
  <img alt="stars" src="https://img.shields.io/github/stars/pooyahpx/HPXPANEL?style=social">
  <img alt="dev" src="https://img.shields.io/badge/dev-hpx-0ea5e9?style=flat-square&logo=github">
</p>

---

## Why this exists

Most panels stop at “create user → copy link.”  
**HPXPANEL** is built for operators who run real fleets: hundreds of accounts, multi-node edges, mixed cores, and clients that need **native VPN protocols** — not only Xray URLs.

Python / FastAPI backend. React command-deck UI. One place for users, nodes, cores, and subscriptions.

---

## What’s actually new (and loud)

### L2TP / IPsec & IKEv2 — native VPN in the panel

This is not a checkbox on a settings page. HPXPANEL wires **real IPsec stacks** into the same user / core workflow you already use:

| Protocol | Why it matters |
| --- | --- |
| **L2TP/IPsec** | Classic, battle-tested tunnel. UDP `500` / `4500` / `1701`. PSK + shared credentials. Works where “another Xray client” is a non-starter. |
| **IKEv2/IPsec** | Modern, certificate-friendly IPsec. Native on Windows, iOS, macOS, Android. Rock-solid reconnects on mobile networks. |

One shared **IPsec username / password** for both L2TP and IKEv2. Core editors for server crypto, PSK, and network — not dump-and-pray JSON.

> If your users live on stock OS VPN settings, this stack is the difference between “install an app” and “just connect.”

### IP Limiter

Cap concurrent unique client IPs per user. Abuse control without babysitting every session.

### Operator UX that doesn’t waste your night

- **Multi-step create-user wizard** — identity → access → limits → advanced, with a live draft rail
- **Subscription page** — usage gauge, metrics rail, traffic chart, protocol links, QR
- **Command-deck UI** — cobalt accents, pixel borders, readable density for long ops sessions
- **Multi-node** + core editors for Xray / WireGuard / IPsec

---

## Protocol coverage

**Proxy / tunnel stack**

- VMess · VLESS · Trojan · Shadowsocks · WireGuard · Hysteria2  
- **L2TP/IPsec · IKEv2/IPsec**  
- TLS · REALITY · multi-protocol per user

**Control plane**

- Full REST API · Telegram bot · CLI · multi-admin RBAC · HWID limits · traffic / expiry / periodic reset · Clash / ClashMeta / V2ray subscription formats

---

## Install on Linux

### One-liner (pick a database)

**TimescaleDB (recommended)**
```bash
sudo bash -c "$(curl -fsSL https://github.com/PasarGuard/scripts/raw/main/pasarguard.sh)" @ install --database timescaledb
```

**SQLite**
```bash
sudo bash -c "$(curl -fsSL https://github.com/PasarGuard/scripts/raw/main/pasarguard.sh)" @ install
```

**MySQL / MariaDB / PostgreSQL**
```bash
sudo bash -c "$(curl -fsSL https://github.com/PasarGuard/scripts/raw/main/pasarguard.sh)" @ install --database mysql
# --database mariadb | postgresql
```

### After install

| | |
| --- | --- |
| Files | `/opt/pasarguard` |
| Config | `/opt/pasarguard/.env` |
| Data | `/var/lib/pasarguard` |
| Dashboard | `https://YOUR_DOMAIN:8000/dashboard/` |

SSL is required for production. For a quick local smoke test without a domain:

```bash
ssh -L 8000:localhost:8000 user@serverip
# → http://localhost:8000/dashboard/
```

Bootstrap the owner account:

```bash
pasarguard cli generate-temp-key
pasarguard --help
```

---

## Install from source (this repo)

```bash
git clone https://github.com/pooyahpx/HPXPANEL.git
cd HPXPANEL

uv sync
uv run alembic upgrade head
uv run main.py

# another terminal
cd dashboard && bun install && bun run dev
```

Dashboard: `http://127.0.0.1:5173/dashboard/`

---

## Stack

- Backend: Python, FastAPI, SQLAlchemy, Alembic  
- Frontend: React, Vite, Tailwind  
- Engines: Xray-core · WireGuard · IPsec (IKEv2 / L2TP)

---

<p align="center">
  <b>dev by <a href="https://github.com/pooyahpx">hpx</a></b><br/>
  <a href="https://github.com/pooyahpx/HPXPANEL">pooyahpx/HPXPANEL</a>
</p>
