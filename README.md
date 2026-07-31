<p align="center">
  <img width="140" height="140" alt="HPX" src="https://raw.githubusercontent.com/pooyahpx/HPXPANEL/main/dashboard/public/statics/brand/hpx-logo.png">
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
**HPXPANEL** is built for operators who run real fleets on **[Xray-core](https://github.com/XTLS/Xray-core)** — with modern tunnels and native VPN in the same console.

Python / FastAPI backend. React command-deck UI. One place for users, nodes, cores, and subscriptions.

---

## Protocol powerhouse

### Xray-core — the daily driver

This is where serious fleets live. HPXPANEL gives you full Xray ops without drowning in JSON:

| Protocol | Why it hits |
| --- | --- |
| **VLESS** | Lightweight, flexible — pairs hard with **REALITY** / TLS under censorship |
| **VMess** | Classic Xray family, enormous client ecosystem |
| **Trojan** | TLS-shaped traffic that blends into normal HTTPS |
| **Shadowsocks** | Simple, proven, everywhere — first-class, not a side quest |

Add **TLS** and **REALITY**, multi-inbound layouts, multi-protocol users, editable Xray cores, and subscriptions that v2rayN / Clash / ClashMeta already understand.

### WireGuard & Hysteria2

When you need a different speed / transport profile next to Xray:

- **WireGuard** — clean crypto, low overhead, excellent throughput  
- **Hysteria2** — aggressive performance on lossy or high-latency paths  

### L2TP / IPsec & IKEv2 — native VPN when the OS is the client

Not every user will install an Xray app. HPXPANEL also wires **real IPsec** into the same user/core workflow:

| Protocol | Why it matters |
| --- | --- |
| **L2TP/IPsec** | Classic tunnel. UDP `500` / `4500` / `1701`. PSK + shared credentials. |
| **IKEv2/IPsec** | Modern, mobile-friendly IPsec. Native on Windows, iOS, macOS, Android. |

One shared **IPsec username / password** for both. Core editors for crypto, PSK, and network.

### Operator extras that actually matter

- **IP Limiter** — cap concurrent unique client IPs  
- **Multi-step create-user wizard** — identity → access → limits → advanced  
- **Subscription page** — usage gauge, metrics rail, traffic chart, QR  
- **Command-deck UI** — cobalt, pixel borders, multi-node + core editors  

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

SSL is required for production. Smoke test without a domain:

```bash
ssh -L 8000:localhost:8000 user@serverip
# → http://localhost:8000/dashboard/
```

```bash
pasarguard cli generate-temp-key
pasarguard --help
```

---

## Install from source

```bash
git clone https://github.com/pooyahpx/HPXPANEL.git
cd HPXPANEL

uv sync
uv run alembic upgrade head
uv run main.py

cd dashboard && bun install && bun run dev
```

Dashboard: `http://127.0.0.1:5173/dashboard/`

---

## Docs

**https://pooyahpx.github.io/HPXPANEL/**

```bash
cd docs && bun install && bun run dev
```

## Stack

- Backend: Python, FastAPI, SQLAlchemy, Alembic  
- Frontend: React, Vite, Tailwind  
- Engines: **Xray-core** · WireGuard · Hysteria2 · IPsec (IKEv2 / L2TP)  
- Docs: VitePress

---

<p align="center">
  <b>dev by <a href="https://github.com/pooyahpx">hpx</a></b><br/>
  <a href="https://github.com/pooyahpx/HPXPANEL">pooyahpx/HPXPANEL</a>
</p>
