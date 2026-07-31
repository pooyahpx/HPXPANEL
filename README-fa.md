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

---

## چرا این پنل؟

بیشتر پنل‌ها همین‌جا تمام می‌شوند: «یوزر بساز → لینک کپی کن.»  
**HPXPANEL** برای اپراتورهایی است که ناوگان واقعی را روی **[Xray-core](https://github.com/XTLS/Xray-core)** می‌چرخانند — با تانل‌های مدرن و VPN نیتیو در همان کنسول.

بک‌اند Python / FastAPI. فرانت React با تم command deck. یک صفحه برای یوزر، نود، کور و سابسکریپشن.

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
