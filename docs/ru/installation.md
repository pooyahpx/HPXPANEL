---
title: Установка
---

# Установка

## Требования

- Linux (Ubuntu / Debian)
- `sudo`
- Домен для SSL

## Одной командой

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

## После установки

| Путь | Назначение |
| --- | --- |
| `/opt/hpxpanel` | Файлы |
| `/opt/hpxpanel/.env` | Конфиг |
| `/var/lib/hpxpanel` | Данные |
| `https://YOUR_DOMAIN:8000/dashboard/` | Дашборд |

```bash
hpxpanel cli forge-seal
```

Тест без домена:

```bash
ssh -L 8000:localhost:8000 user@serverip
```

## Установка HPX Node

На каждом edge-сервере (Linux) запустите инсталлятор. Поднимается Docker-нода с **Xray**, **WireGuard**, **OpenVPN** и **IKEv2** — значения Address / Port / API key / Server CA вставляются в **HPXPANEL → Nodes**.

```bash
sudo bash -c "$(curl -fsSL https://github.com/pooyahpx/HPXNODE/raw/main/scripts/install.sh)" @ install
```

| Путь | Назначение |
| --- | --- |
| `/opt/hpx-node` | Compose |
| `/var/lib/hpx-node` | Серты и конфиги |
| `hpx-node status` / `logs` / `update` | Управление |
