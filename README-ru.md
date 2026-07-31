<p align="center">
  <a href="https://github.com/pooyahpx/HPXPANEL" target="_blank" rel="noopener noreferrer">
    <img width="120" height="120" alt="HPXPANEL" src="https://raw.githubusercontent.com/pooyahpx/HPXPANEL/main/dashboard/public/statics/favicon/android-chrome-192x192.png">
  </a>
</p>

<h1 align="center">HPXPANEL</h1>

<p align="center">
    <strong>Консоль управления прокси — command deck для пользователей, нод, ядер и подписок</strong>
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
 <a href="./README-ru.md">
 🇷🇺 Русский
 </a>
</p>

## 📋 Содержание

> **Быстрая навигация**

-   [📖 Обзор](#-обзор)
    -   [🤔 Почему HPXPANEL?](#-почему-hpxpanel)
        -   [✨ Возможности](#-возможности)
-   [🚀 Установка на Linux](#-установка-на-linux)
-   [🔧 Установка из исходников](#-установка-из-исходников)
-   [💖 Поддержка](#-поддержка)

---

# 📖 Обзор

> **Что такое HPXPANEL?**

HPXPANEL — панель управления прокси с интерфейсом **command deck / ops console**. Управляйте пользователями, нодами, ядрами и подписками из одной удобной плоскости. Написано на **Python / FastAPI** и **React**, поддерживает [Xray-core](https://github.com/XTLS/Xray-core), [WireGuard](https://www.wireguard.com/) и **IPsec / IKEv2 / L2TP**.

---

## 🤔 Почему HPXPANEL?

> **Просто, мощно, узнаваемо**

У HPXPANEL свой визуальный язык: cobalt-акценты, pixel-бордеры, пошаговый мастер создания пользователя, gauge потребления и графики трафика — без лишнего шума.

---

### ✨ Возможности

**🌐 Web UI и API**
- Встроенный **Web UI** с темой command deck
- Полноценный бэкенд **REST API**
- Поддержка **Multi-Node**

**🔐 Протоколы и безопасность**
- **Vmess**, **VLESS**, **Trojan**, **Shadowsocks**, **WireGuard**, **Hysteria2**
- **IPsec / IKEv2 / L2TP**
- **TLS** и **REALITY**
- Несколько протоколов на одного пользователя

**👥 Управление пользователями**
- Пошаговый wizard создания пользователя
- Лимиты **трафика** и **срока действия**
- Периодический сброс трафика
- Лимит **HWID** и **IP Limiter** (макс. одновременных уникальных IP)
- Мульти-пользователь / мульти-inbound сценарии

**🔗 Подписки**
- Ссылки подписки для **V2ray**, **Clash**, **ClashMeta**
- Страница пользователя с gauge, метриками и графиком трафика
- QR-коды и копирование ссылок

**🛠️ Инструменты**
- Редакторы ядер Xray / WireGuard / IPsec
- Интегрированный **Telegram-бот**
- **CLI**
- Мультиязычность и мульти-админ **RBAC**

---

# 🚀 Установка на Linux

> **Быстрый старт** — поднимите HPXPANEL на Linux-сервере за несколько минут

### Требования
- Linux (рекомендуется Ubuntu / Debian)
- Доступ `sudo`
- Домен (для SSL в продакшене)

### Однострочная установка (выберите БД)

**TimescaleDB (рекомендуется):**
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

### 📋 После установки

- **Логи:** смотрите логи сервиса (`Ctrl+C` для остановки)
- **Файлы:** `/opt/pasarguard`
- **Конфиг:** `/opt/pasarguard/.env`
- **Данные:** `/var/lib/pasarguard`
- **Продакшен URL:** `https://YOUR_DOMAIN:8000/dashboard/` (нужен SSL)

**Тест без домена** через SSH port forwarding:

```bash
ssh -L 8000:localhost:8000 user@serverip
```

Откройте: `http://localhost:8000/dashboard/`

> ⚠️ **Только для теста** — закрытие SSH-сессии обрывает доступ.

### 🔧 Следующие шаги

```bash
pasarguard cli generate-temp-key
pasarguard --help
```

---

# 🔧 Установка из исходников

```bash
git clone https://github.com/pooyahpx/HPXPANEL.git
cd HPXPANEL

# Backend
uv sync
uv run alembic upgrade head
uv run main.py

# Dashboard (отдельный терминал)
cd dashboard
bun install
bun run dev
```

Дашборд: `http://127.0.0.1:5173/dashboard/`

---

# 💖 Поддержка

Поставьте звезду и следите за разработкой:

**GitHub:** [pooyahpx/HPXPANEL](https://github.com/pooyahpx/HPXPANEL)  
**dev by hpx:** [github.com/pooyahpx](https://github.com/pooyahpx)

---

<p align="center">
  <a href="https://github.com/pooyahpx">dev by hpx</a>
</p>
