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
