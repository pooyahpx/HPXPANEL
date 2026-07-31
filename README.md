<p align="center">
  <a href="https://github.com/pooyahpx/HPXPANEL" target="_blank" rel="noopener noreferrer">
    <img width="120" height="120" alt="HPXPANEL" src="https://raw.githubusercontent.com/pooyahpx/HPXPANEL/main/dashboard/public/statics/favicon/android-chrome-192x192.png">
  </a>
</p>

<h1 align="center">HPXPANEL</h1>

<p align="center">
    <strong>Command-deck proxy operations console</strong><br/>
    Users · Nodes · Cores · Subscriptions — one sharp control plane.
</p>

---

<br/>
<p align="center">
    <a href="https://github.com/pooyahpx/HPXPANEL/actions/workflows/build.yml" target="_blank">
        <img src="https://img.shields.io/github/actions/workflow/status/pooyahpx/HPXPANEL/build.yml?style=flat-square" />
    </a>
    <a href="https://github.com/pooyahpx/HPXPANEL/blob/main/LICENSE" target="_blank">
        <img src="https://img.shields.io/github/license/pooyahpx/HPXPANEL?style=flat-square" />
    </a>
    <a href="https://github.com/pooyahpx/HPXPANEL" target="_blank">
        <img src="https://img.shields.io/github/stars/pooyahpx/HPXPANEL?style=social" />
    </a>
    <a href="https://github.com/pooyahpx" target="_blank">
        <img src="https://img.shields.io/badge/dev-hpx-0ea5e9?style=flat-square&logo=github" />
    </a>
</p>

<p align="center">
 <a href="./README.md">
 🇺🇸 English
 </a>
 /
 <a href="./README-fa.md">
 🇮🇷 فارسی
 </a>
  /
  <a href="./README-zh-cn.md">
 🇨🇳 简体中文
 </a>
   /
  <a href="./README-ru.md">
 🇷🇺 Русский
 </a>
</p>

## 📋 Table of Contents

> **Quick navigation**

-   [📖 Overview](#-overview)
    -   [🤔 Why HPXPANEL?](#-why-hpxpanel)
        -   [✨ Features](#-features)
-   [🚀 Linux install guide](#-linux-install-guide)
-   [🔧 Install from source](#-install-from-source)
-   [💖 Support](#-support)

---

# 📖 Overview

> **What is HPXPANEL?**

HPXPANEL is a proxy management panel with a custom **command deck / ops console** UI. Manage users, nodes, cores, and subscriptions from one readable control plane. Built with **Python / FastAPI** and **React**, it supports [Xray-core](https://github.com/XTLS/Xray-core), [WireGuard](https://www.wireguard.com/), and **IPsec / IKEv2 / L2TP**.

---

## 🤔 Why HPXPANEL?

> **Simple, powerful, distinct**

HPXPANEL keeps the operator workflow sharp: cobalt accents, pixel borders, a multi-step user wizard, subscription usage gauges, and traffic charts — without drowning you in clutter.

---

### ✨ Features

**🌐 Web UI & API**
- Built-in **Web UI** with command-deck theme
- Full **REST API** backend
- **Multi-Node** infrastructure support

**🔐 Protocols & security**
- **Vmess**, **VLESS**, **Trojan**, **Shadowsocks**, **WireGuard**, **Hysteria2**
- **IPsec / IKEv2 / L2TP**
- **TLS** & **REALITY**
- Multiple protocols per user

**👥 User management**
- Multi-step create-user wizard
- Traffic & expiry limits
- Periodic traffic reset strategies
- **HWID** limit + **IP Limiter** (max concurrent unique IPs)
- Multi-user / multi-inbound workflows

**🔗 Subscriptions**
- Subscription links for **V2ray**, **Clash**, **ClashMeta**
- User delivery page with usage gauge, metrics rail, and traffic chart
- QR codes & copy actions

**🛠️ Tools**
- Xray / WireGuard / IPsec core editors
- Integrated **Telegram bot**
- **CLI**
- Multi-language + multi-admin **RBAC**

---

# 🚀 Linux install guide

> **Quick start** — bring HPXPANEL up on a Linux server in minutes

### Requirements
- Linux (Ubuntu / Debian recommended)
- `sudo` access
- Domain (for SSL in production)

### One-line install (choose database)

**TimescaleDB (recommended):**
```bash
sudo bash -c "$(curl -fsSL https://github.com/PasarGuard/scripts/raw/main/pasarguard.sh)" @ install --database timescaledb
```

**SQLite:**
```bash
sudo bash -c "$(curl -fsSL https://github.com/PasarGuard/scripts/raw/main/pasarguard.sh)" @ install
```

**MySQL:**
```bash
sudo bash -c "$(curl -fsSL https://github.com/PasarGuard/scripts/raw/main/pasarguard.sh)" @ install --database mysql
```

**MariaDB:**
```bash
sudo bash -c "$(curl -fsSL https://github.com/PasarGuard/scripts/raw/main/pasarguard.sh)" @ install --database mariadb
```

**PostgreSQL:**
```bash
sudo bash -c "$(curl -fsSL https://github.com/PasarGuard/scripts/raw/main/pasarguard.sh)" @ install --database postgresql
```

### 📋 After install

- **Logs:** follow service logs (`Ctrl+C` to stop)
- **Files:** `/opt/pasarguard`
- **Config:** `/opt/pasarguard/.env`
- **Data:** `/var/lib/pasarguard`
- **Production URL:** `https://YOUR_DOMAIN:8000/dashboard/` (SSL required)

**Test without a domain** using SSH port forwarding:

```bash
ssh -L 8000:localhost:8000 user@serverip
```

Open: `http://localhost:8000/dashboard/`

> ⚠️ **Testing only** — closing the SSH session drops access.

### 🔧 Next steps

```bash
pasarguard cli generate-temp-key
pasarguard --help
```

---

# 🔧 Install from source

```bash
git clone https://github.com/pooyahpx/HPXPANEL.git
cd HPXPANEL

# Backend
uv sync
uv run alembic upgrade head
uv run main.py

# Dashboard (separate terminal)
cd dashboard
bun install
bun run dev
```

Dashboard: `http://127.0.0.1:5173/dashboard/`

---

# 💖 Support

Star the repo and follow development:

**GitHub:** [pooyahpx/HPXPANEL](https://github.com/pooyahpx/HPXPANEL)  
**dev by hpx:** [github.com/pooyahpx](https://github.com/pooyahpx)

---

<p align="center">
  <a href="https://github.com/pooyahpx">dev by hpx</a>
</p>
