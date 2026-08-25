<p align="center">
  <img width="160" height="160" alt="HPX" src="https://raw.githubusercontent.com/pooyahpx/HPXPANEL/main/dashboard/public/statics/brand/hpx-logo.png">
</p>

<h1 align="center">HPXPANEL</h1>

<p align="center">
  <b>The censorship-resistance command deck.</b><br/>
  <sub>Proxies · VPN · ICMP tunnels · Telegram commerce — one panel, zero duct tape.</sub>
</p>

<p align="center">
  <a href="./README.md">English</a> ·
  <a href="./README-fa.md">فارسی</a> ·
  <a href="./README-ru.md">Русский</a>
</p>

<p align="center">
  <img alt="version" src="https://img.shields.io/badge/release-v3.1.0-8b5cf6?style=for-the-badge">
  <img alt="build" src="https://img.shields.io/github/actions/workflow/status/pooyahpx/HPXPANEL/build.yml?style=for-the-badge&label=CI">
  <img alt="license" src="https://img.shields.io/github/license/pooyahpx/HPXPANEL?style=for-the-badge">
</p>

<p align="center">
  <img alt="telegram" src="https://img.shields.io/badge/Telegram%20Command%20Center-native-26A5E4?style=flat-square&logo=telegram&logoColor=white">
  <img alt="icmp" src="https://img.shields.io/badge/HPX%20ICMP%20Tunnel-built--in-0ea5e9?style=flat-square">
  <img alt="xray" src="https://img.shields.io/badge/Xray--core-full%20ops-6366f1?style=flat-square">
  <img alt="ipsec" src="https://img.shields.io/badge/IKEv2%20%2F%20L2TP%20IPsec-native-10b981?style=flat-square">
  <img alt="stars" src="https://img.shields.io/github/stars/pooyahpx/HPXPANEL?style=social">
</p>

---

## TL;DR — why operators switch

| Other panels | **HPXPANEL** |
| --- | --- |
| Spreadsheet with a login form | **Command-deck NOC UI** — live stats, node scope, cobalt theme |
| “Paste bot token, good luck” | **Native Telegram layer** — shop, support, owner RBAC, auto sub delivery |
| JSON hell for every inbound | **Visual core editors** for Xray, WireGuard, IKEv2, L2TP |
| One protocol, one trick | **Full stack**: VLESS/REALITY, WG, Hysteria2, IPsec, **HPX ICMP** |
| Revoke = support tickets forever | **Sub fingerprint tracking** → new link + QR pushed to buyer automatically |

> **Not a reskin. Not a fork with a logo swap.**  
> Python / FastAPI backend · React 19 command deck · multi-DB · multi-worker · production-grade migrations.

---

## v3.1.0 — HPX ICMP Tunnel

**The panel that manages encrypted ping tunnels — not a bash script in a corner.**

Most ICMP tunnel tools are CLI-only, single-instance, zero observability.  
**HPXPANEL v3.1.0** ships **HPX ICMP** — ChaCha20 traffic inside ICMP, managed like any other infra asset.

<p align="center">
  <b>📡 IRAN ↔ FOREIGN · Docker lifecycle · Health checks · Failover · Telegram alerts</b>
</p>

| Capability | Detail |
| --- | --- |
| **Dual role** | IRAN (client → remote) or FOREIGN (server listen) — one UI |
| **Lifecycle** | Create · start · stop · restart from panel or API |
| **Observability** | Latency, packet loss, interface IP, bytes up/down — live cards |
| **Auto-failover** | Backup tunnel + priority — job switches on unhealthy link |
| **Port forwarding** | IRAN-side DNAT rules from the dashboard |
| **Encrypted secrets** | Tunnel password stored encrypted — not plaintext in DB |
| **RBAC** | Granular `hpx_tunnels` permissions per admin role |
| **Branded core** | `ghcr.io/pooyahpx/hpx-icmp` · interface `hpx0` · container `hpx_tunnel_*` |

**Route:** `Nodes → HPX ICMP` · **API:** `/api/hpx_tunnel`

---

## The first panel with a native Telegram command center

Most panels stop at webhook glue.  
**HPXPANEL** runs commerce, support, and governance **inside the same stack** as your panel.

<p align="center">
  <b>🛍 Sell · 💬 Support · 🛡 Govern · 📡 Auto-deliver subs — from one bot.</b>
</p>

| Feature | What it does |
| --- | --- |
| **🛍 Native shop** | Plans, card-to-card, receipts, test configs, QR delivery |
| **👑 Owner sovereignty** | Promote/demote admins · **fine-grained role permissions** (nodes, settings, user CRUD) |
| **💬 Smart support** | Buyer → all admins · **first reply wins** · ticket locks for everyone else |
| **📋 Owner audit log** | Instant alert when a non-owner admin creates a user |
| **📡 Sold-sub registry** | Owner sees every sub sold via bot — buyer, plan, **live subscription URL** |
| **🔄 Auto sub refresh** | Revoke / config drift detected → **new link + QR to buyer** → owner notified |

---

## Protocol powerhouse

### Xray-core — the daily driver

| Protocol | Why it hits |
| --- | --- |
| **VLESS + REALITY** | TLS-shaped, censorship-resistant — with built-in **REALITY target scanner** |
| **VMess · Trojan · Shadowsocks** | Full family, first-class — not side quests |
| **Multi-inbound layouts** | Edit cores visually · push to nodes · subscription-aware |

### WireGuard · Hysteria2

- **WireGuard** — subnet usage dashboard, peer pools, low overhead  
- **Hysteria2** — when the path is lossy and you need aggression  

### L2TP / IPsec · IKEv2 — when the OS is the client

| Protocol | Why it matters |
| --- | --- |
| **L2TP/IPsec** | Classic tunnel · PSK + shared credentials |
| **IKEv2/IPsec** | Native on Windows, iOS, macOS, Android |

One shared IPsec identity workflow. Core editors for crypto, PSK, and network.

### Operator extras

- **IP Limiter** — cap concurrent unique client IPs per user  
- **Multi-step user wizard** — identity → access → limits → advanced  
- **Subscription page** — usage gauge, metrics rail, traffic chart, QR  
- **Admin RBAC** — scoped permissions, API keys, role templates  
- **REALITY scanner** — probe decoy domains for TLS 1.3 + HTTP/2 suitability before you commit  

---

## Screenshots

### REALITY target scanner

<p align="center">
  <img src="./docs/assets/readme/reality-scan.png" alt="REALITY target scanner" width="820">
</p>

<p align="center"><i>Multi-host probe · suitable-only filter · live latency chips</i></p>

### Command deck statistics

<p align="center">
  <img src="./docs/assets/readme/statistics-command-deck.png" alt="Statistics command deck" width="820">
</p>

<p align="center"><i>Nodes scope · CPU / RAM / disk · traffic · online users</i></p>

### Multi-core protocols

<p align="center">
  <img src="./docs/assets/readme/core-protocol-picker.png" alt="Core protocol picker" width="420">
</p>

<p align="center"><i>Xray · WireGuard · IKEv2 · L2TP — one console</i></p>

---

## Install on Linux

### One-liner

**TimescaleDB (recommended)**
```bash
sudo bash -c "$(curl -fsSL https://github.com/pooyahpx/HPXPANEL/raw/main/scripts/hpxpanel.sh)" @ install --database timescaledb
```

**SQLite**
```bash
sudo bash -c "$(curl -fsSL https://github.com/pooyahpx/HPXPANEL/raw/main/scripts/hpxpanel.sh)" @ install
```

**MySQL · MariaDB · PostgreSQL**
```bash
sudo bash -c "$(curl -fsSL https://github.com/pooyahpx/HPXPANEL/raw/main/scripts/hpxpanel.sh)" @ install --database mysql
```

### After install

| | |
| --- | --- |
| Files | `/opt/hpxpanel` |
| Config | `/opt/hpxpanel/.env` |
| Data | `/var/lib/hpxpanel` |
| Dashboard | `https://YOUR_DOMAIN:8000/dashboard/` |

```bash
hpxpanel cli forge-seal   # create first admin
alembic upgrade head      # includes hpx_tunnels (v3.1.0+)
```

### HPX Node (edge servers)

```bash
sudo bash -c "$(curl -fsSL https://github.com/pooyahpx/HPXNODE/raw/main/scripts/install.sh)" @ install
```

Deploys Docker node with **Xray · WireGuard · OpenVPN · IKEv2** — prints values for **HPXPANEL → Nodes**.

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

Dashboard dev: `http://127.0.0.1:5173/dashboard/`

---

## Changelog highlights

| Version | Headline |
| --- | --- |
| **v3.1.0** | **HPX ICMP Tunnel** — panel-managed ChaCha20 ping tunnels, health, failover, RBAC |
| v2.5.x | Sold-sub registry with live URLs · auto sub delivery · Telegram fingerprint tracking |
| v2.4.x | Admin permission bot · support ticket locking · owner audit log |
| v2.3.x | Native Telegram shop · card-to-card · test configs |

---

## Docs · Donate · Stack

| | |
| --- | --- |
| **Docs** | https://pooyahpx.github.io/HPXPANEL/ |
| **Donate** | https://pooyahpx.github.io/HPXPANEL/donate/ |
| **Backend** | Python 3.14 · FastAPI · SQLAlchemy · Alembic · APScheduler |
| **Frontend** | React 19 · Vite · Tailwind 4 · shadcn/ui |
| **Engines** | Xray-core · WireGuard · Hysteria2 · IPsec · **HPX ICMP** |
| **Databases** | SQLite · PostgreSQL · TimescaleDB · MySQL · MariaDB |

---

<p align="center">
  <b>Built by <a href="https://github.com/pooyahpx">hpx</a></b><br/>
  <a href="https://github.com/pooyahpx/HPXPANEL">github.com/pooyahpx/HPXPANEL</a><br/>
  <sub>If this panel saves you hours — ⭐ star the repo.</sub>
</p>
