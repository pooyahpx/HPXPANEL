---
title: مقدمه
description: HPXPANEL چیست و چرا برای اپراتور ساخته شده
outline: deep
---

# مقدمه

# HPXPANEL

**کنسول عملیات پروکسی به سبک command deck** — پنل تولیدمحور برای یوزر، نود، کور و سابسکریپشن.

HPXPANEL برای اپراتورهایی است که ناوگان واقعی دارند: صدها اکانت، چند نود، چند کور، و کلاینت‌هایی که به **VPN نیتیو سیستم‌عامل** نیاز دارند — نه فقط لینک Xray. بک‌اند **Python / FastAPI**، داشبورد **React**، انجین **Xray-core**، **WireGuard** و **IPsec (IKEv2 / L2TP)**.

## چرا HPXPANEL؟

بیشتر پنل‌ها همین‌جا تمام می‌شوند: «یوزر بساز → لینک کپی کن.» HPXPANEL جلوتر می‌رود:

- **استک VPN نیتیو** — L2TP/IPsec و IKEv2 داخل همان جریان یوزر/کور
- **UI تیز برای اپراتور** — تم کبالت، فریم پیکسلی، تراکم خوانا برای شیفت‌های طولانی
- **کنترل سوءاستفاده** — IP Limiter و محدودیت HWID
- **تحویل شفاف به یوزر** — صفحه سابسکریپشن با گیج مصرف، متریک و نمودار
- **اتوماسیون** — REST API، ربات تلگرام، CLI، RBAC چند‌ادمین

## ویژگی‌های کلیدی

### قابلیت‌های اصلی

- **Web UI** با تم command deck
- بک‌اند کامل **REST API**
- پشتیبانی **Multi-Node**
- پروتکل‌ها: VMess، VLESS، Trojan، Shadowsocks، WireGuard، Hysteria2
- **L2TP/IPsec** و **IKEv2/IPsec**
- چند پروتکل روی یک یوزر، محدودیت ترافیک و انقضا، ریست دوره‌ای

### امکانات اپراتور

- **ویزارد چندمرحله‌ای** ساخت یوزر
- **IP Limiter** (سقف IP یکتای همزمان)
- لینک سابسکریپشن V2Ray / Clash / ClashMeta
- QR، ربات تلگرام، CLI
- TLS و REALITY، داشبورد چندزبانه

## شروع سریع

1. نصب روی لینوکس — [نصب](/fa/installation)
2. ساخت کلید موقت owner با CLI
3. ورود به داشبورد و ساخت اکانت owner
4. پیکربندی کور (از جمله IPsec) — [L2TP و IKEv2](/fa/protocols/ipsec)

## جامعه و حمایت

- **GitHub:** [pooyahpx/HPXPANEL](https://github.com/pooyahpx/HPXPANEL)
- **dev by hpx:** [github.com/pooyahpx](https://github.com/pooyahpx)

---

آماده‌ای؟ برو سراغ [راهنمای نصب لینوکس](/fa/installation).
