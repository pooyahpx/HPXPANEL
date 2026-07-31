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
**HPXPANEL** — для операторов с реальным флотом: сотни аккаунтов, несколько нод, разные ядра и клиенты, которым нужен **нативный VPN ОС**, а не только Xray-URL.

Бэкенд Python / FastAPI. React UI в стиле command deck. Один контур для пользователей, нод, ядер и подписок.

---

## Что реально новое (и об этом стоит говорить громко)

### L2TP / IPsec и IKEv2 — настоящий VPN внутри панели

Это не галочка в настройках. HPXPANEL встраивает **живой IPsec-стек** в тот же user / core workflow:

| Протокол | Почему важно |
| --- | --- |
| **L2TP/IPsec** | Классический, проверенный туннель. UDP `500` / `4500` / `1701`. PSK + общие credentials. Там, где «поставь ещё один Xray-клиент» не вариант. |
| **IKEv2/IPsec** | Современный IPsec с сертификатами. Нативно на Windows, iOS, macOS, Android. Стабильные реконнекты в мобильных сетях. |

Один общий **IPsec username / password** для L2TP и IKEv2. Редакторы ядра для crypto, PSK и сети — без «кинь JSON и молись».

> Если пользователи подключаются через встроенный VPN системы — это путь от «ставь приложение» к «просто Connect».

### IP Limiter

Лимит одновременных уникальных IP на пользователя. Контроль абьюза без ручного мониторинга каждой сессии.

### UX оператора, который не сжигает ночь

- **Пошаговый wizard создания пользователя** — identity → access → limits → advanced с live-черновиком
- **Страница подписки** — gauge расхода, метрики, график трафика, ссылки протоколов, QR
- **Command-deck UI** — cobalt, pixel-бордеры, читаемая плотность для длинных смен
- **Multi-node** + редакторы ядер Xray / WireGuard / IPsec

---

## Покрытие протоколов

**Прокси / туннели**

- VMess · VLESS · Trojan · Shadowsocks · WireGuard · Hysteria2  
- **L2TP/IPsec · IKEv2/IPsec**  
- TLS · REALITY · несколько протоколов на одного пользователя

**Control plane**

- Полный REST API · Telegram-бот · CLI · multi-admin RBAC · HWID · трафик / expiry / периодический сброс · подписки Clash / ClashMeta / V2ray

---

## Установка на Linux

### Одной командой (выберите БД)

**TimescaleDB (рекомендуется)**
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

### После установки

| | |
| --- | --- |
| Файлы | `/opt/pasarguard` |
| Конфиг | `/opt/pasarguard/.env` |
| Данные | `/var/lib/pasarguard` |
| Дашборд | `https://YOUR_DOMAIN:8000/dashboard/` |

Для продакшена нужен SSL. Быстрый тест без домена:

```bash
ssh -L 8000:localhost:8000 user@serverip
# → http://localhost:8000/dashboard/
```

Создание owner:

```bash
pasarguard cli generate-temp-key
pasarguard --help
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

## Стек

- Backend: Python, FastAPI, SQLAlchemy, Alembic  
- Frontend: React, Vite, Tailwind  
- Engines: Xray-core · WireGuard · IPsec (IKEv2 / L2TP)

---

<p align="center">
  <b>dev by <a href="https://github.com/pooyahpx">hpx</a></b><br/>
  <a href="https://github.com/pooyahpx/HPXPANEL">pooyahpx/HPXPANEL</a>
</p>
