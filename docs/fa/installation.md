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

::: tip پیشنهادی
برای استقرارهای پر از متریک، **TimescaleDB** بهتر است.
:::

## بعد از نصب

| مسیر | کاربرد |
| --- | --- |
| `/opt/hpxpanel` | فایل‌های برنامه |
| `/opt/hpxpanel/.env` | پیکربندی |
| `/var/lib/hpxpanel` | داده پایدار |
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
hpxpanel cli forge-seal
hpxpanel --help
```

کلید یک‌بارمصرف را در صفحه لاگین داشبورد بزنید و اکانت owner بسازید.

## نصب نود HPX

روی هر سرور لبه (Linux) اینستالر نود HPX را اجرا کن. نود Docker با **Xray**، **WireGuard**، **OpenVPN** و **IKEv2** بالا می‌آید و مقادیر Address / Port / API key / Server CA را برای ثبت در **HPXPANEL → Nodes** چاپ می‌کند.

```bash
sudo bash -c "$(curl -fsSL https://github.com/pooyahpx/HPXNODE/raw/main/scripts/install.sh)" @ install
```

| مسیر | کاربرد |
| --- | --- |
| `/opt/hpx-node` | compose |
| `/var/lib/hpx-node` | گواهی و کانفیگ |
| `hpx-node status` / `logs` / `update` | مدیریت |

## بعدی

- [نصب از سورس](/fa/source)
- [L2TP و IKEv2 / IPsec](/fa/protocols/ipsec)
- [کاربران و محدودیت‌ها](/fa/users)
