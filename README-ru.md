<p align="center">
  <img width="140" height="140" alt="HPX" src="https://raw.githubusercontent.com/pooyahpx/HPXPANEL/main/dashboard/public/statics/brand/hpx-logo.png">
</p>

<h1 align="center">HPXPANEL</h1>

<p align="center">
  <b>Консоль, которая видит прокси как инфраструктуру — а не как таблицу.</b>
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

## Зачем это нужно

Большинство панелей заканчиваются на «создай юзера → скопируй ссылку».  
**HPXPANEL** — для операторов, которые крутят реальный флот на **[Xray-core](https://github.com/XTLS/Xray-core)** — с современными туннелями и нативным VPN в той же консоли.

Бэкенд Python / FastAPI. React UI в стиле command deck. Один контур для пользователей, нод, ядер и подписок.

---

## Сила протоколов

### Xray-core — ежедневный драйвер флота

Здесь живут серьёзные деплои. HPXPANEL даёт полный Xray-ops без утопления в JSON:

| Протокол | Почему мощно |
| --- | --- |
| **VLESS** | лёгкий и гибкий — жёстко сочетается с **REALITY** / TLS под цензурой |
| **VMess** | классика Xray, огромная экосистема клиентов |
| **Trojan** | трафик похож на обычный HTTPS |
| **Shadowsocks** | простой, проверенный, вездесущий — first-class |

Плюс **TLS** и **REALITY**, multi-inbound, multi-protocol users, редакторы Xray core и подписки для v2rayN / Clash / ClashMeta.

### WireGuard и Hysteria2

Когда рядом с Xray нужен другой профиль скорости / транспорта:

- **WireGuard** — чистая крипта, низкий overhead, отличный throughput  
- **Hysteria2** — агрессивная производительность на плохих/latency-путях  

### L2TP / IPsec и IKEv2 — нативный VPN, когда клиент = ОС

Не каждый пользователь поставит Xray-клиент. HPXPANEL также встраивает **живой IPsec** в тот же user/core workflow:

| Протокол | Почему важно |
| --- | --- |
| **L2TP/IPsec** | классический туннель. UDP `500` / `4500` / `1701`. PSK + общие credentials. |
| **IKEv2/IPsec** | современный mobile-friendly IPsec. Нативно на Windows, iOS, macOS, Android. |

Один общий **IPsec username / password**. Редакторы ядра для crypto, PSK и сети.

### Операторские плюсы

- **IP Limiter** — лимит одновременных уникальных IP  
- **Пошаговый wizard** создания пользователя  
- **Страница подписки** — gauge, метрики, график, QR  
- **Command-deck UI** — cobalt, pixel-бордеры, multi-node + редакторы ядер  

---

## Установка на Linux

### Одной командой (выберите БД)

**TimescaleDB (рекомендуется)**
```bash
sudo bash -c "$(curl -fsSL https://github.com/pooyahpx/HPXPANEL/raw/main/scripts/hpxpanel.sh)" @ install --database timescaledb
```

**SQLite**
```bash
sudo bash -c "$(curl -fsSL https://github.com/pooyahpx/HPXPANEL/raw/main/scripts/hpxpanel.sh)" @ install
```

**MySQL / MariaDB / PostgreSQL**
```bash
sudo bash -c "$(curl -fsSL https://github.com/pooyahpx/HPXPANEL/raw/main/scripts/hpxpanel.sh)" @ install --database mysql
# --database mariadb | postgresql
```

### После установки

| | |
| --- | --- |
| Файлы | `/opt/hpxpanel` |
| Конфиг | `/opt/hpxpanel/.env` |
| Данные | `/var/lib/hpxpanel` |
| Дашборд | `https://YOUR_DOMAIN:8000/dashboard/` |

Для продакшена нужен SSL. Быстрый тест без домена:

```bash
ssh -L 8000:localhost:8000 user@serverip
# → http://localhost:8000/dashboard/
```

Создание owner:

```bash
hpxpanel cli forge-seal
hpxpanel --help
```

---

## Установка из исходников (этот репозиторий)

```bash
git clone https://github.com/pooyahpx/HPXPANEL.git
cd HPXPANEL

uv sync
uv run alembic upgrade head
uv run main.py

# другой терминал
cd dashboard && bun install && bun run dev
```

Дашборд: `http://127.0.0.1:5173/dashboard/`

---

## Документация

**https://pooyahpx.github.io/HPXPANEL/ru/**

```bash
cd docs && bun install && bun run dev
```

## Стек

- Backend: Python, FastAPI, SQLAlchemy, Alembic  
- Frontend: React, Vite, Tailwind  
- Engines: **Xray-core** · WireGuard · Hysteria2 · IPsec (IKEv2 / L2TP)
- Docs: VitePress

---

<p align="center">
  <b>dev by <a href="https://github.com/pooyahpx">hpx</a></b><br/>
  <a href="https://github.com/pooyahpx/HPXPANEL">pooyahpx/HPXPANEL</a>
</p>
