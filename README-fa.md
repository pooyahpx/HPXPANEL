<p align="center">
  <img width="160" height="160" alt="HPX" src="https://raw.githubusercontent.com/pooyahpx/HPXPANEL/main/dashboard/public/statics/brand/hpx-logo.png">
</p>

<h1 align="center">HPXPANEL</h1>

<p align="center">
  <b>دِک فرمان مقاومت در برابر سانسور.</b><br/>
  <sub>پروکسی · VPN · تونل ICMP · فروش تلگرام — یک پنل، بدون وصله.</sub>
</p>

<p align="center">
  <a href="./README.md">English</a> ·
  <a href="./README-fa.md">فارسی</a> ·
  <a href="./README-ru.md">Русский</a>
</p>

<p align="center">
  <img alt="version" src="https://img.shields.io/badge/release-v3.1.0-8b5cf6?style=for-the-badge">
  <img alt="build" src="https://img.shields.io/github/actions/workflow/status/pooyahpx/HPXPANEL/build.yml?style=for-the-badge&label=CI">
  <img alt="license" src="https://img.shields.io/github/license/pooyahpx/HPXPANEL?style=for-the-badge">
</p>

<p align="center">
  <img alt="telegram" src="https://img.shields.io/badge/مرکز%20فرمان%20تلگرام-نیتیو-26A5E4?style=flat-square&logo=telegram&logoColor=white">
  <img alt="icmp" src="https://img.shields.io/badge/تونل%20HPX%20ICMP-داخلی-0ea5e9?style=flat-square">
  <img alt="xray" src="https://img.shields.io/badge/Xray--core-عملیات%20کامل-6366f1?style=flat-square">
  <img alt="ipsec" src="https://img.shields.io/badge/IKEv2%20%2F%20L2TP%20IPsec-نیتیو-10b981?style=flat-square">
  <img alt="stars" src="https://img.shields.io/github/stars/pooyahpx/HPXPANEL?style=social">
</p>

---

## خلاصه — چرا اپراتورها می‌آیند اینجا

| پنل‌های معمولی | **HPXPANEL** |
| --- | --- |
| اکسل با لاگین | **UI فرماندهی NOC** — آمار زنده، scope نود، تم command deck |
| «توکن بات بده» | **لایه تلگرام نیتیو** — فروشگاه، پشتیبانی، RBAC مالک، تحویل خودکار ساب |
| JSON برای هر inbound | **ادیتور بصری کور** برای Xray، WireGuard، IKEv2، L2TP |
| یک پروتکل، یک ترفند | **استک کامل**: VLESS/REALITY، WG، Hysteria2، IPsec، **HPX ICMP** |
| revoke = تیکت بی‌پایان | **ردیابی fingerprint ساب** → لینک + QR خودکار برای خریدار |

> **ری‌اسکین نیست. فورک با لوگو عوض‌شده نیست.**  
> بک‌اند Python / FastAPI · فرانت React 19 · چند دیتابیس · migration حرفه‌ای.

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
| **برند HPX** | `pooyahpx/hpx-icmp` · اینترفیس `hpx0` |

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

## نصب سریع

```bash
sudo bash -c "$(curl -fsSL https://github.com/pooyahpx/HPXPANEL/raw/main/scripts/hpxpanel.sh)" @ install --database timescaledb
```

```bash
hpxpanel cli forge-seal
alembic upgrade head   # شامل hpx_tunnels (v3.1.0+)
```

**داشبورد:** `https://YOUR_DOMAIN:8000/dashboard/`

---

## تغییرات مهم

| نسخه | |
| --- | --- |
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
