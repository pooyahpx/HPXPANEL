<p align="center">
  <img width="160" height="160" alt="HPX" src="https://raw.githubusercontent.com/pooyahpx/HPXPANEL/main/dashboard/public/statics/brand/hpx-logo.png">
</p>

<h1 align="center">HPXPANEL</h1>

<p align="center">
  <b>دِک فرمان مقاومت در برابر سانسور.</b><br/>
  <sub>پروکسی · VPN · ICMP · <b>تونل‌های Reverse با HPX Pulse</b> · فروش تلگرام — یک پنل، بدون وصله.</sub>
</p>

<p align="center">
  <a href="./README.md">English</a> ·
  <a href="./README-fa.md">فارسی</a> ·
  <a href="./README-ru.md">Русский</a>
</p>

<p align="center">
  <img alt="version" src="https://img.shields.io/badge/release-v3.11.17-8b5cf6?style=for-the-badge">
  <img alt="build" src="https://img.shields.io/github/actions/workflow/status/pooyahpx/HPXPANEL/build.yml?style=for-the-badge&label=CI">
  <img alt="license" src="https://img.shields.io/github/license/pooyahpx/HPXPANEL?style=for-the-badge">
</p>

<p align="center">
  <img alt="pulse" src="https://img.shields.io/badge/HPX%20Pulse-13%20پروفایل%20·%20پینگ%20زنده-a855f7?style=flat-square">
  <img alt="telegram" src="https://img.shields.io/badge/مرکز%20فرمان%20تلگرام-نیتیو-26A5E4?style=flat-square&logo=telegram&logoColor=white">
  <img alt="icmp" src="https://img.shields.io/badge/تونل%20HPX%20ICMP-داخلی-0ea5e9?style=flat-square">
  <img alt="xray" src="https://img.shields.io/badge/Xray--core-عملیات%20کامل-6366f1?style=flat-square">
  <img alt="ipsec" src="https://img.shields.io/badge/IKEv2%20%2F%20L2TP%20IPsec-نیتیو-10b981?style=flat-square">
  <img alt="stars" src="https://img.shields.io/github/stars/pooyahpx/HPXPANEL?style=social">
</p>

## نصب سریع — یک دستور کافی است

روی **Linux با root**. نصب‌کننده خودکار همه پیش‌نیازها را نصب می‌کند: **Docker · Compose · curl · jq · yq · openssl · socat · DNS tools · migration دیتابیس** (داخل کانتینر). نیازی به `apt install` جداگانه یا `alembic upgrade head` روی سرور نیست.

**TimescaleDB (پیشنهادی)**
```bash
sudo bash -c "$(curl -fsSL https://github.com/pooyahpx/HPXPANEL/raw/main/scripts/hpxpanel.sh)" @ install --database timescaledb
```

**SQLite · MySQL · MariaDB · PostgreSQL**
```bash
sudo bash -c "$(curl -fsSL https://github.com/pooyahpx/HPXPANEL/raw/main/scripts/hpxpanel.sh)" @ install
sudo bash -c "$(curl -fsSL https://github.com/pooyahpx/HPXPANEL/raw/main/scripts/hpxpanel.sh)" @ install --database mysql
```

بعد از نصب:
```bash
hpxpanel cli forge-seal   # ساخت اولین ادمین
hpxpanel install-node     # اختیاری: نود روی همین سرور (تست / homelab)
hpxnode                   # نمایش Address / API key / Server CA
```

بعد برو **HPXPANEL → Nodes** و مقادیر `hpxnode` را paste کن. راهنمای کامل: [بعد از نصب](#بعد-از-نصب-و-دستورات-مهم).

**داشبورد:** `https://YOUR_DOMAIN:8000/dashboard/`

**HPX Pulse — نصب دستی engine تونل** (سرور ایران، اگر `join` روی دانلود mirror پنل گیر کرد):
```bash
curl --http1.1 --connect-timeout 20 --max-time 300 -fsSL \
  https://raw.githubusercontent.com/pooyahpx/HPXPANEL/main/scripts/hpx-tunnel-engine-install.sh | \
  sudo env HPX_PREFER_GITHUB=1 bash

sudo hpx-pulse-agent sync
```

---

## 🔥 تنها پنلی که کل زرادخانه را یک‌جا دارد

پنل‌های دیگر معمولاً فقط **یوزر + سابسکریپشن** می‌دهند. تمام.  
تونل؟ اسکریپت جدا. فروش؟ بات وصله‌ای. ICMP؟ پروژهٔ دیگری. Stealth؟ منوی شخص ثالث روی دو سرور.

**HPXPANEL** اولین دِک فرمان است که این معاملهٔ احمقانه را قبول نمی‌کند.

| بقیه | **HPXPANEL — همه در یک جا** |
| --- | --- |
| یا پنل Xray یا ابزار تونل یا فروش تلگرام | **Xray + VPN + ICMP + Pulse Reverse + فروشگاه تلگرام** |
| TOML دستی / منوی CLI روی دو VPS | **مشاور ۱۳ پروفایل رتبه‌بندی می‌کند → یک‌کلیک agent ایران و خارج** |
| یک پینگ نمایشی که بعدش مرده | **پینگ زنده هر ۵ ثانیه** روی مسیر واقعی کاربر (ایران:۴۴۳) |
| «خودت ufw باز کن» | Agent فایروال را باز می‌کند · اگر Xray خارج بالا نباشد هشدار می‌دهد |
| یا stealth یا speed یا mux — هر کدام یک محصول | **Stealth · TCP · Mux · WSS · KCP · QUIC · ICMP · Direct L3** — با امتیاز برای هدف تو |

> **ری‌اسکین نیست. عوض کردن لوگو نیست. «یک دکمه اضافه کردیم» نیست.**  
> این همان پنلی است که اپراتور وقتی می‌خواهد **کل جعبه ابزار جنگ** را داشته باشد باز می‌کند — پروکسی، VPN، ICMP، تونل Reverse Stealth، فروشگاه، پشتیبانی، RBAC — بدون چسباندن پنج ریپو به هم.

---

## ⚡ HPX Pulse — مشاوری که تونل Reverse را مثل یک سلاح رتبه‌بندی می‌کند

**Stealth. Balanced. Speed.** هدف را بگو. استک را امتیاز می‌دهد. Deploy کن. تمام.

<p align="center">
  <img src="./docs/images/hpx-pulse/01-advisor-wizard.png" alt="ویزارد HPX Pulse Advisor" width="720">
</p>

<p align="center"><i>نام · هدف · IP ایران/خارج · پورت تونل تصادفی (تاس) · فوروارد ساده ایران → خارج (مثلاً ۴۴۳ → ۴۴۳)</i></p>

### سه حالت هدف — نه سه برچسب تبلیغاتی

<p align="center">
  <img src="./docs/images/hpx-pulse/02-goal-modes.png" alt="stealth balanced speed" width="420">
</p>

| حالت | کی فشارش می‌دهی |
| --- | --- |
| **stealth** | DPI شکار می‌کند. TCP Stealth با لایه Noise. بدون نمایش TLS جعلی. |
| **balanced** | کار روزمره. فیلتر را رد کن بدون ذوب کردن VPS تک‌هسته. |
| **speed** | مسیر تمیز. اول throughput. کمتر استتار، بیشتر فشار خام. |

### سیزده پروفایل امتیازدار — زرادخانه واقعی، نه لیست تبلیغاتی

<p align="center">
  <img src="./docs/images/hpx-pulse/03-ranked-profiles.png" alt="پروفایل‌های پیشنهادی Pulse" width="720">
</p>

<p align="center"><i>Reverse TCP Stealth با امتیاز ۱۰۰ · TCP · WS · Mux · WSS · KCP+FEC · QUIC · ICMP · UDP · Direct L3 — انتخاب کن، بساز، agent بفرست</i></p>

**توپولوژی Reverse همان‌طور که اپراتور ایران واقعاً کار می‌کند:** ایران گوش می‌دهد · خارج dial می‌کند · کاربر به ایران:۴۴۳ می‌زند · ترافیک روی Xray خارج می‌نشیند.  
**Direct L3** وقتی لوله لایه۳ می‌خواهی. همان ویزارد. همان agent. همان برند — **HPX** تا آخر.

### کارت‌های زنده NOC — agent سبز، پینگ زنده، مسیر صادق

<p align="center">
  <img src="./docs/images/hpx-pulse/04-live-tunnels.png" alt="تونل‌های زنده HPX Pulse" width="900">
</p>

<p align="center"><i>Running · REVERSE · STEALTH · ایران/خارج connected · ms زنده · «user path OK (Iran:8443)»</i></p>

| چیزی که می‌بینی | چرا فرق دارد |
| --- | --- |
| **پینگ زنده** | حدود هر ۵ ثانیه — مسیر **واقعی کاربر**، نه عدد نمایشی یک‌باره |
| **وضعیت agent** | ایران + خارج claimed/connected — بدون باستان‌شناسی SSH |
| **سلامت مسیر** | اگر کنترل بالا باشد ولی :۴۴۳ مرده، کارت می‌گوید — کانفیگ بی‌صدا `-1` نمی‌شود |
| **دستور یک‌خطی** | توکن join برای هر دو طرف — curl، join، تمام |

**مسیر UI:** `HPX Pulse` · **API:** `/api/hpx_pulse` · **Agent:** `scripts/hpx-pulse-agent.sh`

### نصب Agent (ایران + خارج)

1. در پنل: **HPX Pulse** → ساخت تونل → **Tokens** → دستور هر طرف را کپی کنید.
2. روی **سرور ایران** (توکن `hpxpi_…`):

```bash
curl --http1.1 --connect-timeout 20 --max-time 300 -fsSL \
  https://raw.githubusercontent.com/pooyahpx/HPXPANEL/main/scripts/hpx-pulse-agent.sh | \
  sudo bash -s -- join hpxpi_توکن_واقعی \
  --panel-url https://آدرس_پنل:8000 --side iran
```

3. روی **سرور خارج** (توکن `hpxpa_…`) — همان دستور با `--side abroad`.

> حتماً توکن واقعی از پنل باشد (`hpxpi_` / `hpxpa_`). کلمه `TOKEN` خطای 422 می‌دهد.

### نصب Engine تونل — خودکار + دستی

در `join`، agent یک‌بار **`hpx-tunnel-engine`** را در `/usr/local/bin/hpx-tunnel-engine` نصب می‌کند.

| منبع | کی |
| --- | --- |
| **GitHub** (پیش‌فرض ایران) | سرور ایران — mirror پنل روی پورت `:8000` اغلب از داخل ایران باز نیست |
| **Mirror پنل** | سرور خارج، یا وقتی GitHub فیلتر است |
| **فایل محلی** | آفلاین: `hpx-tunnel-engine_linux_amd64.tar.gz` + `SHA256SUMS` در `/opt/hpx-pulse/engine/` |

**اگر join گیر کرد** روی `Downloading HPX tunnel engine from panel mirror…`:

```bash
# ۱) نصب engine از GitHub (پیشنهادی برای ایران)
curl --http1.1 --connect-timeout 20 --max-time 300 -fsSL \
  https://raw.githubusercontent.com/pooyahpx/HPXPANEL/main/scripts/hpx-tunnel-engine-install.sh | \
  sudo env HPX_PREFER_GITHUB=1 bash

# ۲) ادامه setup (اگر join قبلاً claim شده)
sudo hpx-pulse-agent sync
```

یا بعد از نصب agent:

```bash
sudo hpx-pulse-agent install-engine
sudo hpx-pulse-agent sync
```

**تست نصب مجدد engine:**
```bash
sudo hpx-pulse-agent uninstall-engine
sudo hpx-pulse-agent install-engine --force
```

**بررسی:**

```bash
ls -la /usr/local/bin/hpx-tunnel-engine
sudo hpx-pulse-agent status
```

| متغیر محیطی | اثر |
| --- | --- |
| `HPX_PREFER_GITHUB=1` | دانلود engine از GitHub اول (ایران) |
| `HPX_NO_GITHUB_FALLBACK=1` | فقط mirror پنل / فایل محلی |
| `HPX_ENGINE_LOCAL_DIR=/path` | استفاده از `.tar.gz` آفلاین |

**پنل باید از ایران برای heartbeat/sync در دسترس باشد** (نه فقط موقع join). پورت `:8000` اغلب فیلتر است — پنل را روی **443** (nginx → panel) بگذارید و در `.env` پنل:

```bash
PANEL_PUBLIC_URL=https://panel.example.com
```

دوباره **Tokens** بگیرید. روی سرور ایران اگر قبلاً join شده:

```bash
sudo hpx-pulse-agent set-panel-url https://panel.example.com
sudo hpx-pulse-agent sync
```

تست از ایران: `curl -I --connect-timeout 10 https://panel.example.com/api/hpx_pulse/agent/hpx-pulse-agent.sh`

**چند Pulse روی یک سرور ایران:** از v3.8.21 هر pulse سرویس جدا `hpx-pulse-tunnel-<id>` دارد. پورت listen ایران (مثلاً `443`) را بین دو pulse مشترک نکنید — بهتر است **یک pulse با چند port forward** (`443`، `2053`، …) بسازید.

---

## خلاصه — چرا اپراتورها می‌آیند اینجا

| پنل‌های معمولی | **HPXPANEL** |
| --- | --- |
| اکسل با لاگین | **UI فرماندهی NOC** — آمار زنده، scope نود، تم command deck |
| «توکن بات بده» | **لایه تلگرام نیتیو** — فروشگاه، پشتیبانی، RBAC مالک، تحویل خودکار ساب |
| JSON برای هر inbound | **ادیتور بصری کور** برای Xray، WireGuard، IKEv2، L2TP |
| یک پروتکل، یک ترفند | **استک کامل**: VLESS/REALITY، WG، Hysteria2، IPsec، **HPX ICMP**، **HPX Pulse** |
| تونل = محصول جدا | **مشاور Pulse + تونل Reverse/Direct زنده داخل خود پنل** |
| revoke = تیکت بی‌پایان | **ردیابی fingerprint ساب** → لینک + QR خودکار برای خریدار |

> **ری‌اسکین نیست. فورک با لوگو عوض‌شده نیست.**  
> بک‌اند Python / FastAPI · فرانت React 19 · چند دیتابیس · migration حرفه‌ای.

---

## v3.3.0 — ویزارد تونل + Auto-Heal

**ICMP = بدون پورت.** تونل HPX فقط بسته‌های ping رمزنگاری‌شده بین دو IP عمومی رد و بدل می‌کند — نیازی به باز کردن TCP/UDP نیست.

**FOREIGN روی سرور پنل** اجرا می‌شود (Docker از داخل کانتینر پنل + `docker.sock`). **IRAN** فقط با agent روی VPS ایران.

| قابلیت جدید | توضیح |
| --- | --- |
| **ویزارد ۳ مرحله‌ای** | FOREIGN (همین سرور) → IRAN (join token) → Done |
| **Auto-heal قانون‌محور** | container down، iface busy، keepalive، agent stale — بدون LLM |
| **Diagnose & Repair** | دکمه روی کارت تونل + badge آخرین تعمیر |
| **Preflight** | بررسی Linux · Docker · docker.sock · NET_ADMIN قبل از استارت |
| **پیش‌فرض‌ها** | MTU=1000 · Keepalive=30 · `icmp_echo_ignore_all=1` روی هر دو سرور |

---

## v3.1.0 — تونل HPX ICMP

**پنلی که تونل ping رمزنگاری‌شده را مثل هر asset زیرساختی مدیریت می‌کند.**

اکثر ابزارهای ICMP فقط CLI، تک‌نمونه، بدون مانیتورینگ‌اند.  
**HPXPANEL v3.1.0** **HPX ICMP** را می‌آورد — ترافیک ChaCha20 داخل ICMP.

<p align="center">
  <b>📡 ایران ↔ خارج · Docker · Health check · Failover · هشدار تلگرام</b>
</p>

| قابلیت | توضیح |
| --- | --- |
| **دو نقش** | IRAN (کلاینت) یا FOREIGN (سرور) — یک UI |
| **Lifecycle** | ساخت · استارت · استاپ · ری‌استارت از پنل یا API |
| **مانیتورینگ** | Latency، packet loss، IP اینترفیس، ترافیک — کارت زنده |
| **Failover خودکار** | تونل پشتیبان + اولویت |
| **Port forwarding** | قوانین DNAT سمت IRAN از داشبورد |
| **رمز امن** | password تونل رمزنگاری‌شده در DB |
| **RBAC** | دسترسی `hpx_tunnels` برای هر نقش ادمین |
| **برند HPX** | ایمیج محلی `hpx-icmp` (دانلود خودکار) · اینترفیس `hpx0` |

**مسیر:** `HPX ICMP` (سایدبار) · **API:** `/api/hpx_tunnel`

### Agent ایران (بدون پنل سنگین روی ایران)

1. در پنل یک تونل **IRAN** بساز (IP سرور FOREIGN + رمز مشترک).
2. **join token / دستور یک‌خطی** را کپی کن.
3. روی VPS ایران (فقط Docker — بدون UI پنل):

```bash
curl -fsSL https://raw.githubusercontent.com/pooyahpx/HPXPANEL/main/scripts/hpx-tunnel-agent.sh | sudo bash
```

نصب‌کننده منوی تعاملی باز می‌کند:
1. **وصل با join token پنل** — آدرس پنل + توکن را می‌پرسد، کانفیگ را نشان می‌دهد، IP ریموت را می‌توانی تأیید/عوض کنی
2. **ستاپ دستی** — IP سرور خارج، رمز، اینترفیس، IP محلی و … را می‌پرسد

بعد `hpx-icmp` را استارت می‌زند و (در حالت پنل) هر ~۳۰ثانیه sync می‌کند. تونل‌های **FOREIGN** همچنان با Docker روی هاست پنل اجرا می‌شوند.



---

## اولین پنل با مرکز فرمان تلگرام نیتیو

| امکان | کاربرد |
| --- | --- |
| **🛍 فروشگاه** | پلن، کارت‌به‌کارت، رسید، کانفیگ تست، QR |
| **👑 حاکمیت مالک** | ادمین/حذف · **دسترسی نقش‌ها** (نود، تنظیمات، CRUD یوزر) |
| **💬 پشتیبانی** | **اولین پاسخ مالک تیکت** — بقیه قفل |
| **📋 لاگ مالک** | ساخت یوزر توسط ادمین غیرمالک → اعلان فوری |
| **📡 رجیستری ساب فروخته** | مالک همه ساب‌ها را با **URL زنده** می‌بیند |
| **🔄 آپدیت خودکار ساب** | revoke / تغییر کانفیگ → لینک + QR برای خریدار |

---

## قدرت پروتکل‌ها

**Xray:** VLESS + REALITY (با اسکنر REALITY) · VMess · Trojan · Shadowsocks  
**WireGuard · Hysteria2** · **IKEv2/L2TP IPsec** · **IP Limiter** · **REALITY scanner**

---

---

## بعد از نصب و دستورات مهم

### چک‌لیست اولین بار

| مرحله | دستور / کار |
| --- | --- |
| ۱. ساخت ادمین | `hpxpanel cli forge-seal` |
| ۲. (اختیاری) SSL | `hpxpanel ssl` |
| ۳. نصب نود | `hpxpanel install-node` — یا روی **سرور جدا** (پیشنهاد production) |
| ۴. دیدن اطلاعات نود | `hpxnode` |
| ۵. ثبت در پنل | **Nodes → Create** — Address، Node port، API port، API key، Server CA |
| ۶. Core و Host | از UI — Xray / WireGuard / VPN core، بعد Host و کاربر |

| مورد | مسیر |
| --- | --- |
| پنل | `/opt/hpxpanel` |
| تنظیمات | `/opt/hpxpanel/.env` |
| داده | `/var/lib/hpxpanel` |
| داشبورد | `https://YOUR_DOMAIN:8000/dashboard/` |

> پنل + نود روی **یک** سرور برای تست خوبه؛ برای فروش تجاری بهتره جدا باشن.

### دستورات `hpxpanel`

```bash
hpxpanel help
```

| دستور | کار |
| --- | --- |
| `up` / `down` / `restart` | روشن / خاموش / ری‌استارت کانتینر پنل |
| `status` | وضعیت کانتینر |
| `logs` | لاگ زنده (`logs --no-follow` بدون follow) |
| `update` | آپدیت به آخرین نسخه + نصب `hpxnode` روی نودهای قبلی |
| `install-node` | نصب نود HPX روی همین سرور |
| `ssl` | صدور / تمدید Let's Encrypt |
| `cli` / `tui` | CLI / TUI پنل |
| `edit-env` | ویرایش `.env` |
| `edit` | ویرایش `docker-compose.yml` |
| `backup` / `restore` | بکاپ و ریستور دیتابیس |
| `backup-service` | بکاپ زمان‌بندی‌شده (مثلاً تلگرام) |
| `core-update` | آپدیت core روی همه نودها |
| `purge` | پاک‌سازی کامل (داده + DB) — **برگشت‌ناپذیر** |
| `uninstall` | حذف پنل (داده می‌ماند مگر purge) |

بعد از ویرایش `.env`: `hpxpanel restart`

**نصب با گزینه‌ها:**
```bash
# نسخه مشخص
sudo bash -c "$(curl -fsSL https://github.com/pooyahpx/HPXPANEL/raw/main/scripts/hpxpanel.sh)" @ install --database timescaledb --version v3.11.17

# SSL هنگام نصب
sudo bash -c "$(curl -fsSL https://github.com/pooyahpx/HPXPANEL/raw/main/scripts/hpxpanel.sh)" @ install --database timescaledb --ssl-domain panel.example.com
```

### نود HPX (سرور edge)

**Xray · WireGuard · OpenVPN · IKEv2** — خروجی برای **HPXPANEL → Nodes**.

```bash
hpxpanel install-node

# مستقل روی هر سرور Linux:
sudo bash -c "$(curl -fsSL https://github.com/pooyahpx/HPXPANEL/raw/main/scripts/hpx-node.sh)" @ install -y
```

**هر وقت اطلاعات نود را ببین:**
```bash
hpxnode
hpx-node info
hpx-node status
hpx-node logs
hpxnode --name shop1    # چند نود روی یک سرور
```

| فایل | محتوا |
| --- | --- |
| `/var/lib/hpx-node/register-in-panel.txt` | کپی فیلدهای ثبت نود |
| `/var/lib/hpx-node/certs/ssl_cert.pem` | Server CA برای paste در پنل |

**چند نود روی یک ماشین:**
```bash
sudo bash -c "$(curl -fsSL https://github.com/pooyahpx/HPXPANEL/raw/main/scripts/hpx-node.sh)" @ install -y --name shop1 --service-port 62051
hpx-node list
```

### HPX Copilot (دستیار AI)

دکمه ✨ در داشبورد. پیش‌فرض: **Groq** (رایگان).

1. کلید API رایگان: https://console.groq.com/keys  
2. `hpxpanel edit-env`:

```env
COPILOT_ENABLED=true
COPILOT_PROVIDER=groq
OPENAI_API_KEY=gsk_YOUR_KEY_HERE
COPILOT_MODEL=openai/gpt-oss-20b
COPILOT_BASE_URL=https://api.groq.com/openai
```

3. `hpxpanel restart`

Copilot context زنده پنل را می‌خواند و می‌تواند لینک `vless` / `vmess` را import کند (inbound لازم را خودش می‌سازد).

### عیب‌یابی

| مشکل | راه‌حل |
| --- | --- |
| خطای `socat` / `apt` در نصب | `apt-get update && apt-get install -y socat` و دوباره نصب |
| `hpxnode: command not found` | `hpxpanel update` |
| OpenVPN `Authentication Failed` | پروفایل را دوباره دانلود کن؛ احراز هویت با **certificate** است نه یوزر/پسورد |
| Pulse از ایران به پنل نمی‌رسد | `PANEL_PUBLIC_URL=https://دامنه` در `.env`، پنل روی **443** |
| پورت ۸۰۰۰ اشغال | پورت دیگر در installer یا `UVICORN_PORT` در `.env` |
| rate limit Groq | مدل `openai/gpt-oss-20b` یا صبر کن |

---

## تغییرات مهم

| نسخه | |
| --- | --- |
| **v3.11.x** | **HPX Copilot** (Groq) · دستور `hpxnode` · ساخت inbound از share link · بهبود installer |
| **v3.3.0** | **ویزارد تونل ICMP** · auto-heal · diagnose/repair · preflight |
| **v3.1.0** | **تونل HPX ICMP** — مدیریت از پنل، health، failover، RBAC |
| v2.5.x | رجیستری ساب فروخته · تحویل خودکار · fingerprint |
| v2.4.x | دسترسی ادمین در بات · قفل تیکت · لاگ مالک |

---

## مستندات

**https://pooyahpx.github.io/HPXPANEL/**

---

<p align="center">
  <b>ساخته‌شده توسط <a href="https://github.com/pooyahpx">hpx</a></b><br/>
  <a href="https://github.com/pooyahpx/HPXPANEL">github.com/pooyahpx/HPXPANEL</a><br/>
  <sub>اگر این پنل وقتت را ذخیره کرد — ⭐ استار بده.</sub>
</p>
