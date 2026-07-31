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

## После установки

| Путь | Назначение |
| --- | --- |
| `/opt/pasarguard` | Файлы |
| `/opt/pasarguard/.env` | Конфиг |
| `/var/lib/pasarguard` | Данные |
| `https://YOUR_DOMAIN:8000/dashboard/` | Дашборд |

```bash
pasarguard cli generate-temp-key
```

Тест без домена:

```bash
ssh -L 8000:localhost:8000 user@serverip
```

## Установка HPX Node

На каждом edge-сервере (Linux) запустите инсталлятор. Поднимается Docker-нода с **Xray**, **WireGuard**, **OpenVPN** и **IKEv2** — значения Address / Port / API key / Server CA вставляются в **HPXPANEL → Nodes**.

```bash
sudo bash -c "$(curl -fsSL https://github.com/pooyahpx/HPXPANEL/raw/main/scripts/hpx-node.sh)" @ install
```

| Путь | Назначение |
| --- | --- |
| `/opt/hpx-node` | Compose |
| `/var/lib/hpx-node` | Серты и конфиги |
| `hpx-node status` / `logs` / `update` | Управление |
