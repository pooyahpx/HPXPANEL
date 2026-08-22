<p align="center">
  <img width="140" height="140" alt="HPX" src="https://raw.githubusercontent.com/pooyahpx/HPXPANEL/main/dashboard/public/statics/brand/hpx-logo.png">
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

<p align="center">
  <img alt="version" src="https://img.shields.io/badge/version-v2.5.0-8b5cf6?style=flat-square">
  <img alt="telegram bot" src="https://img.shields.io/badge/Telegram%20Bot-built--in-26A5E4?style=flat-square&logo=telegram&logoColor=white">
  <img alt="shop" src="https://img.shields.io/badge/Shop%20%26%20Support-native-10b981?style=flat-square">
</p>

---

## چرا این پنل؟

بیشتر پنل‌ها همین‌جا تمام می‌شوند: «یوزر بساز → لینک کپی کن.»  
**HPXPANEL** برای اپراتورهایی است که ناوگان واقعی را روی **[Xray-core](https://github.com/XTLS/Xray-core)** می‌چرخانند — با تانل‌های مدرن و VPN نیتیو در همان کنسول.

بک‌اند Python / FastAPI. فرانت React با تم command deck. یک صفحه برای یوزر، نود، کور و سابسکریپشن.

---

## اولین پنل با مرکز فرمان تلگرام نیتیو

بیشتر پنل‌ها همین‌جا می‌ایستند: «توکن بات بده و دعا کن.»  
**HPXPANEL** یک **لایه تلگرام کامل** دارد — فروشگاه، پشتیبانی، کنترل مالک، و تحویل خودکار ساب — همه داخل همان استک پنل. بدون ربات ریسلر third-party. بدون وصله.

<p align="center">
  <b>🛍 فروش · 💬 پشتیبانی · 🛡 حاکمیت مالک · 📡 تحویل خودکار ساب — از یک بات.</b>
</p>

### امکانات آماده از روز اول

| امکان | کاربرد |
| --- | --- |
| **🛍 فروشگاه نیتیو** | پلن، کارت‌به‌کارت، رسید، کانفیگ تست، QR |
| **👑 حاکمیت مالک** | ادمین/حذف ادمین، **تنظیم دسترسی نقش‌ها** (نود، تنظیمات، ساخت/حذف یوزر) |
| **💬 پشتیبانی هوشمند** | پیام خریدار برای همه ادمین‌ها؛ **اولین پاسخ مالک تیکت است** — بقیه قفل |
| **📋 لاگ مالک** | وقتی ادمین (غیرمالک) یوزر می‌سازد → پیام فوری با گروه، حجم، تاریخ |
| **📡 رجیستری ساب فروخته** | مالک همه ساب‌های فروخته‌شده از بات را می‌بیند — خریدار، پلن، لینک زنده |
| **🔄 به‌روزرسانی خودکار ساب** | پنل تغییر ساب را تشخیص می‌دهد (revoke، تغییر کانفیگ) → **لینک + QR فقط برای همان خریدار** → اطلاع به مالک |

### چرا برای اپراتور مهم است

- **خریدار داخل تلگرام می‌ماند** — سفارش، پرداخت، دریافت کانفیگ، آپدیت ساب  
- **ادمین‌ها بی‌حد و حصر نمی‌شوند** — مالک مشخص می‌کند چه کسی نود ری‌استارت کند یا تنظیمات را عوض کند  
- **پشتیبانی بدون هرج‌ومرج** — هر تیکت یک ادمین؛ بدون پاسخ تکراری  
- **revoke ≠ کابوس پشتیبانی** — چرخش ساب خودکار detect و push می‌شود  

> **v2.5.0** — ردیابی اثرانگشت ساب، تحویل خودکار به خریدار، داشبورد ساب‌های فروخته برای مالک  
> **v2.4.0** — مدیریت دسترسی ادمین در بات، قفل تیکت پشتیبانی، لاگ ساخت یوزر برای مالک  

---

## قدرت پروتکل‌ها

### Xray-core — ران روزانه فلیت

اینجا جایی است که فلیت‌های جدی زندگی می‌کنند. HPXPANEL عملیات کامل Xray می‌دهد، بدون غرق شدن در JSON:

| پروتکل | چرا می‌ترکاند |
| --- | --- |
| **VLESS** | سبک و انعطاف‌پذیر — جفت قوی با **REALITY** / TLS زیر سانسور |
| **VMess** | خانواده کلاسیک Xray، اکوسیستم کلاینت عظیم |
| **Trojan** | ترافیک شبیه HTTPS معمولی |
| **Shadowsocks** | ساده، امتحان‌پسند، همه‌جا — first-class، نه آپشن فرعی |

به‌علاوه **TLS** و **REALITY**، چند inbound، چند پروتکل روی یک یوزر، ادیتور کور Xray، و سابسکریپشنی که v2rayN / Clash / ClashMeta می‌فهمند.

### WireGuard و Hysteria2

وقتی کنار Xray به پروفایل سرعت / ترانزپورت دیگری نیاز داری:

- **WireGuard** — کریپتوی تمیز، سربار کم، throughput عالی  
- **Hysteria2** — عملکرد تهاجمی روی مسیرهای پر‌تلفات یا با تأخیر بالا  

### L2TP / IPsec و IKEv2 — VPN نیتیو وقتی کلاینت خودِ OS است

هر یوزری کلاینت Xray نصب نمی‌کند. HPXPANEL استک **IPsec واقعی** را هم به همان جریان یوزر/کور وصل می‌کند:

| پروتکل | چرا مهم است |
| --- | --- |
| **L2TP/IPsec** | تانل کلاسیک. UDP `500` / `4500` / `1701`. PSK + کرِدِنشیال مشترک. |
| **IKEv2/IPsec** | IPsec مدرن و موبایل‌پسند. نیتیو روی Windows، iOS، macOS، Android. |

یک **یوزرنیم / پسورد مشترک IPsec** برای هر دو. ادیتور کور برای کریپتو، PSK و شبکه.

### امکانات اپراتور که واقعاً به درد می‌خورد

- **IP Limiter** — سقف IP یکتای همزمان  
- **ویزارد چندمرحله‌ای ساخت یوزر**  
- **صفحه سابسکریپشن** — گیج مصرف، متریک، نمودار، QR  
- **UI command deck** — کبالت، border پیکسلی، مولتی‌نود + ادیتور کور  

---

## اسکرین‌شات‌ها

### اسکنر هدف REALITY

قبل از اینکه دامنه‌ای را به Xray وصل کنی، آن را به‌عنوان decoy اسکن کن. پنل **TLS 1.3**، **HTTP/2 (ALPN)** و latency را چک می‌کند و هدف‌های مناسب را مشخص می‌کند.

<p align="center">
  <img src="./docs/assets/readme/reality-scan.png" alt="اسکن هدف REALITY" width="820">
</p>

<p align="center"><i>اسکن Reality — چند هدف، فیلتر Suitable only، بج TLS 1.3 / H2 و latency</i></p>

<p align="center">
  <img src="./docs/assets/readme/reality-target-detail.png" alt="جزئیات هدف Suitable Reality" width="820">
</p>

<p align="center"><i>جزئیات هدف — SNI، TLS، H2، تبادل کلید / PQ، سرتیفیکت و SANها</i></p>

### آمار Command Deck

نمای NOC زنده: لیست نودها، متریک سیستم، ترافیک و یوزر آنلاین.

<p align="center">
  <img src="./docs/assets/readme/statistics-command-deck.png" alt="آمار HPXPANEL" width="820">
</p>

<p align="center"><i>Statistics — اسکوپ نود، CPU / RAM / Disk، ترافیک و کاربران آنلاین</i></p>

### انتخاب هسته / پروتکل

یک کنسول برای **Xray**، **WireGuard**، **IKEv2/IPsec** و **L2TP/IPsec**.

<p align="center">
  <img src="./docs/assets/readme/core-protocol-picker.png" alt="انتخاب نوع Core" width="420">
</p>

<p align="center"><i>انتخاب نوع Core — جابه‌جایی بین استک‌ها بدون خروج از پنل</i></p>

---

## نصب روی لینوکس

### یک خطی (دیتابیس را انتخاب کن)

**TimescaleDB (پیشنهادی)**
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

### بعد از نصب

| | |
| --- | --- |
| فایل‌ها | `/opt/hpxpanel` |
| کانفیگ | `/opt/hpxpanel/.env` |
| دیتا | `/var/lib/hpxpanel` |
| داشبورد | `https://YOUR_DOMAIN:8000/dashboard/` |

برای پروداکشن SSL لازم است. تست سریع بدون دامنه:

```bash
ssh -L 8000:localhost:8000 user@serverip
# → http://localhost:8000/dashboard/
```

راه‌اندازی اکانت owner:

```bash
hpxpanel cli forge-seal
hpxpanel --help
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

## مستندات

**https://pooyahpx.github.io/HPXPANEL/fa/**

```bash
cd docs && bun install && bun run dev
```

## استک

- بک‌اند: Python، FastAPI، SQLAlchemy، Alembic  
- فرانت: React، Vite، Tailwind  
- انجین‌ها: **Xray-core** · WireGuard · Hysteria2 · IPsec (IKEv2 / L2TP)
- Docs: VitePress

---

<p align="center">
  <b>dev by <a href="https://github.com/pooyahpx">hpx</a></b><br/>
  <a href="https://github.com/pooyahpx/HPXPANEL">pooyahpx/HPXPANEL</a>
</p>
