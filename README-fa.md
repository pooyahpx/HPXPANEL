<p align="center">
  <img width="96" height="96" alt="HPXPANEL" src="https://raw.githubusercontent.com/pooyahpx/HPXPANEL/main/dashboard/public/statics/favicon/android-chrome-192x192.png">
</p>

<h1 align="center">HPXPANEL</h1>

<p align="center">
  <b>کنسول عملیاتی که پروکسی را مثل زیرساخت می‌بیند — نه مثل اکسل.</b>
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

## چرا این پنل؟

بیشتر پنل‌ها همین‌جا تمام می‌شوند: «یوزر بساز → لینک کپی کن.»  
**HPXPANEL** برای اپراتورهایی است که ناوگان واقعی دارند: صدها اکانت، چند نود، چند کور، و کلاینت‌هایی که به **VPN نیتیو سیستم‌عامل** نیاز دارند — نه فقط URL از نوع Xray.

بک‌اند Python / FastAPI. فرانت React با تم command deck. یک صفحه برای یوزر، نود، کور و سابسکریپشن.

---

## چیزهایی که واقعاً جدیدند (و باید بلند گفته شوند)

### L2TP / IPsec و IKEv2 — VPN واقعی داخل پنل

این یک تیک ساده توی تنظیمات نیست. HPXPANEL استک **IPsec واقعی** را به همان جریان یوزر / کور وصل می‌کند:

| پروتکل | چرا مهم است |
| --- | --- |
| **L2TP/IPsec** | تانل کلاسیک و امتحان‌پسند. UDP `500` / `4500` / `1701`. با PSK و کرِدِنشیال مشترک. جایی که «یک کلاینت Xray دیگر نصب کن» جواب نیست، این جواب است. |
| **IKEv2/IPsec** | IPsec مدرن، دوست‌دار گواهی. نیتیو روی Windows، iOS، macOS، Android. ریکانکت محکم روی شبکه موبایل. |

یک **یوزرنیم / پسورد مشترک IPsec** برای هر دو پروتکل. ادیتور کور برای کریپتو، PSK و شبکه — نه JSON رها‌شده.

> اگر یوزرهات با VPN خودِ سیستم‌عامل وصل می‌شن، این استک فاصلهٔ «اپ نصب کن» تا «فقط Connect بزن» است.

### IP Limiter

سقف IP یکتای همزمان برای هر یوزر. کنترل سوءاستفاده بدون نشستن پای هر سشن.

### UX اپراتور که شب را حرام نمی‌کند

- **ویزارد چندمرحله‌ای ساخت یوزر** — هویت → دسترسی → محدودیت → پیشرفته، با پیش‌نمایش زنده
- **صفحه سابسکریپشن** — گیج مصرف، ریل متریک، نمودار ترافیک، لینک پروتکل‌ها، QR
- **UI به سبک command deck** — کبالت، border پیکسلی، تراکم خوانا برای شیفت‌های طولانی
- **Multi-node** + ادیتور کور برای Xray / WireGuard / IPsec

---

## پوشش پروتکل‌ها

**استک پروکسی / تانل**

- VMess · VLESS · Trojan · Shadowsocks · WireGuard · Hysteria2  
- **L2TP/IPsec · IKEv2/IPsec**  
- TLS · REALITY · چند پروتکل روی یک یوزر

**کنترل‌پلین**

- REST API کامل · ربات تلگرام · CLI · RBAC چند‌ادمین · محدودیت HWID · ترافیک / انقضا / ریست دوره‌ای · فرمت سابسکریپشن Clash / ClashMeta / V2ray

---

## نصب روی لینوکس

### یک خطی (دیتابیس را انتخاب کن)

**TimescaleDB (پیشنهادی)**
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

### بعد از نصب

| | |
| --- | --- |
| فایل‌ها | `/opt/pasarguard` |
| کانفیگ | `/opt/pasarguard/.env` |
| دیتا | `/var/lib/pasarguard` |
| داشبورد | `https://YOUR_DOMAIN:8000/dashboard/` |

برای پروداکشن SSL لازم است. تست سریع بدون دامنه:

```bash
ssh -L 8000:localhost:8000 user@serverip
# → http://localhost:8000/dashboard/
```

راه‌اندازی اکانت owner:

```bash
pasarguard cli generate-temp-key
pasarguard --help
```

---

## نصب از سورس (همین ریپو)

```bash
git clone https://github.com/pooyahpx/HPXPANEL.git
cd HPXPANEL

uv sync
uv run alembic upgrade head
uv run main.py

# ترمینال جدا
cd dashboard && bun install && bun run dev
```

داشبورد: `http://127.0.0.1:5173/dashboard/`

---

## استک

- بک‌اند: Python، FastAPI، SQLAlchemy، Alembic  
- فرانت: React، Vite، Tailwind  
- انجین‌ها: Xray-core · WireGuard · IPsec (IKEv2 / L2TP)

---

<p align="center">
  <b>dev by <a href="https://github.com/pooyahpx">hpx</a></b><br/>
  <a href="https://github.com/pooyahpx/HPXPANEL">pooyahpx/HPXPANEL</a>
</p>
