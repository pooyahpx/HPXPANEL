---
dir: rtl
title: نصب
description: نصب HPXPANEL روی لینوکس
---

# نصب

> شروع سریع — پنل را روی سرور لینوکس در چند دقیقه بالا بیاورید.

## پیش‌نیازها

- لینوکس (Ubuntu / Debian پیشنهادی)
- دسترسی `sudo`
- دامنه برای SSL پروداکشن

## نصب یک‌خطی

دیتابیس را انتخاب کنید:

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

::: tip پیشنهادی
برای استقرارهای پر از متریک، **TimescaleDB** بهتر است.
:::

## بعد از نصب

| مسیر | کاربرد |
| --- | --- |
| `/opt/pasarguard` | فایل‌های برنامه |
| `/opt/pasarguard/.env` | پیکربندی |
| `/var/lib/pasarguard` | داده پایدار |
| `https://YOUR_DOMAIN:8000/dashboard/` | داشبورد پروداکشن |

::: warning SSL لازم است
داشبورد پروداکشن به TLS نیاز دارد. قبل از لانچ، گواهی دامنه بگیرید.
:::

## تست بدون دامنه

```bash
ssh -L 8000:localhost:8000 user@serverip
```

سپس: `http://localhost:8000/dashboard/`

::: danger فقط تست
با بستن SSH دسترسی قطع می‌شود.
:::

## راه‌اندازی owner

```bash
pasarguard cli generate-temp-key
pasarguard --help
```

کلید یک‌بارمصرف را در صفحه لاگین داشبورد بزنید و اکانت owner بسازید.

## بعدی

- [نصب از سورس](/fa/source)
- [L2TP و IKEv2 / IPsec](/fa/protocols/ipsec)
- [کاربران و محدودیت‌ها](/fa/users)
