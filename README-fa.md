<p align="center">
  <a href="https://github.com/pooyahpx/HPXPANEL" target="_blank" rel="noopener noreferrer">
    <img width="120" height="120" alt="HPXPANEL" src="https://raw.githubusercontent.com/pooyahpx/HPXPANEL/main/dashboard/public/statics/favicon/android-chrome-192x192.png">
  </a>
</p>

<h1 align="center">HPXPANEL</h1>

<p align="center">
    <strong>کنسول عملیات پروکسی — command deck برای یوزر، نود، کور و سابسکریپشن</strong>
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

## 📋 فهرست مطالب

> **ناوبری سریع** — به هر بخش زیر پرش کنید

-   [📖 بررسی اجمالی](#-بررسی-اجمالی)
    -   [🤔 چرا HPXPANEL؟](#-چرا-hpxpanel)
        -   [✨ ویژگی‌ها](#-ویژگیها)
-   [🚀 راهنمای نصب روی لینوکس](#-راهنمای-نصب-روی-لینوکس)
-   [🔧 نصب از سورس](#-نصب-از-سورس)
-   [💖 حمایت](#-حمایت)

---

# 📖 بررسی اجمالی

> **HPXPANEL چیست؟**

HPXPANEL یک پنل مدیریت پروکسی با رابط **command deck / ops console** است؛ برای اپراتورهایی که می‌خواهند صدها اکانت، نود و کور را از یک داشبورد تیز و خوانا کنترل کنند. بک‌اند با **Python / FastAPI** و فرانت با **React** ساخته شده و از [Xray-core](https://github.com/XTLS/Xray-core)، [WireGuard](https://www.wireguard.com/) و **IPsec / IKEv2 / L2TP** پشتیبانی می‌کند.

---

## 🤔 چرا HPXPANEL؟

> **ساده، قدرتمند، متمایز**

به‌جای یک پنل عمومی، HPXPANEL یک زبان بصری اختصاصی دارد: کبالت، borderهای پیکسلی، ویزارد ساخت کاربر، گیج مصرف سابسکریپشن و نمودار ترافیک. مدیریت کاربران، محدودیت‌ها، نودها و لینک اشتراک — همه از یک کنسول.

---

### ✨ ویژگی‌ها

<div align="right">

**🌐 رابط کاربری وب و API**
- داشبورد **Web UI** با تم command deck
- بک‌اند کاملاً **REST API**
- پشتیبانی از **Multi-Node** برای توزیع زیرساخت

**🔐 پروتکل‌ها و امنیت**
- پشتیبانی از **Vmess**، **VLESS**، **Trojan**، **Shadowsocks**، **WireGuard**، **Hysteria2**
- پشتیبانی از **IPsec / IKEv2 / L2TP**
- پشتیبانی از **TLS** و **REALITY**
- **چند پروتکل** برای یک کاربر

**👥 مدیریت کاربران**
- ویزارد چندمرحله‌ای ساخت کاربر
- محدودیت‌های **ترافیک** و **تاریخ انقضا**
- محدودیت ترافیک **دوره‌ای** (روزانه، هفتگی و غیره)
- محدودیت **HWID** و **IP Limiter** (سقف IP همزمان)
- **چند کاربر** روی یک inbound / چند inbound روی یک پورت

**🔗 اشتراک‌ها و اشتراک‌گذاری**
- **لینک اشتراک** سازگار با **V2ray**، **Clash** و **ClashMeta**
- صفحه سابسکریپشن با گیج مصرف، متریک‌ها و نمودار ترافیک
- تولیدکننده **QRcode** و کپی لینک

**🛠️ ابزارها و سفارشی‌سازی**
- ادیتور کور Xray / WireGuard / IPsec
- **ربات تلگرام** یکپارچه
- **CLI**
- **چند زبان** و **چند ادمین** با **RBAC**

</div>

---

# 🚀 راهنمای نصب روی لینوکس

> **شروع سریع** — HPXPANEL را روی سرور لینوکس در چند دقیقه بالا بیاورید

### پیش‌نیازها
- لینوکس (Ubuntu / Debian پیشنهاد می‌شود)
- دسترسی `sudo`
- دامنه (برای SSL در پروداکشن)

### نصب سریع با اسکریپت (بر اساس دیتابیس)

**TimescaleDB (توصیه شده):**
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

### 📋 پس از نصب

<div align="right">

**📋 لاگ‌ها را ببینید** (برای توقف `Ctrl+C`)

**📁 فایل‌ها:** `/opt/pasarguard`

**⚙️ پیکربندی:** `/opt/pasarguard/.env`

**💾 داده:** `/var/lib/pasarguard`

**🔒 مهم:** برای امنیت، داشبورد به SSL نیاز دارد  
دسترسی پروداکشن: `https://YOUR_DOMAIN:8000/dashboard/`

**🔗 تست بدون دامنه:** از SSH port forwarding استفاده کنید

</div>

```bash
ssh -L 8000:localhost:8000 user@serverip
```

سپس باز کنید: `http://localhost:8000/dashboard/`

> ⚠️ **فقط برای تست** — با بستن ترمینال SSH دسترسی قطع می‌شود.

### 🔧 مراحل بعدی

```bash
# ساخت کلید موقت برای راه‌اندازی حساب owner
pasarguard cli generate-temp-key

# راهنما
pasarguard --help
```

---

# 🔧 نصب از سورس

اگر می‌خواهید مستقیم از ریپوی HPXPANEL روی لینوکس کار کنید:

```bash
# کلون
git clone https://github.com/pooyahpx/HPXPANEL.git
cd HPXPANEL

# بک‌اند
uv sync
uv run alembic upgrade head
uv run main.py

# داشبورد (ترمینال جدا)
cd dashboard
bun install
bun run dev
```

داشبورد معمولاً روی `http://127.0.0.1:5173/dashboard/` و API روی پورت بک‌اند در دسترس است.

---

# 💖 حمایت

<div align="right">

اگر HPXPANEL براتون مفیده، ستاره بزنید و توسعه را دنبال کنید:

**GitHub:** [pooyahpx/HPXPANEL](https://github.com/pooyahpx/HPXPANEL)  
**dev by hpx:** [github.com/pooyahpx](https://github.com/pooyahpx)

</div>

---

<p align="center">
  <a href="https://github.com/pooyahpx">dev by hpx</a>
</p>
