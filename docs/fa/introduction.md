---
dir: rtl
title: مقدمه
description: HPXPANEL چیست و چرا برای اپراتور ساخته شده
outline: deep
---

# مقدمه

# HPXPANEL

**کنسول عملیات پروکسی به سبک command deck** — پنل تولیدمحور برای یوزر، نود، کور و سابسکریپشن.

قلب سیستم **[Xray-core](https://github.com/XTLS/Xray-core)** است: VMess، VLESS، Trojan، Shadowsocks، TLS و REALITY — کنار **WireGuard**، **Hysteria2** و در صورت نیاز **IPsec (IKEv2 / L2TP)**. بک‌اند **Python / FastAPI**، داشبورد **React**.

## چرا HPXPANEL؟

- **قدرت Xray** — VLESS / VMess / Trojan / Shadowsocks با TLS و REALITY، چند inbound، چند پروتکل روی یک یوزر
- **تانل‌های مدرن** — WireGuard و Hysteria2 برای پروفایل سرعت/ترانزپورت متفاوت
- **VPN نیتیو وقتی لازم است** — L2TP/IPsec و IKEv2 برای کلاینت خودِ OS
- **UI تیز برای اپراتور** — تم command deck
- **کنترل سوءاستفاده** — IP Limiter و HWID
- **تحویل شفاف** — صفحه سابسکریپشن با گیج و نمودار
- **اتوماسیون** — REST API، تلگرام، CLI، RBAC

## ویژگی‌های کلیدی

### قابلیت‌های اصلی

- **Web UI** با تم command deck
- بک‌اند کامل **REST API** و **Multi-Node**
- **استک Xray:** VMess، VLESS، Trojan، Shadowsocks (+ TLS / REALITY)
- **WireGuard** و **Hysteria2**
- **L2TP/IPsec** و **IKEv2/IPsec**
- محدودیت ترافیک / انقضا / ریست دوره‌ای

### امکانات اپراتور

- ویزارد چندمرحله‌ای ساخت یوزر
- **IP Limiter**
- سابسکریپشن V2Ray / Clash / ClashMeta
- ادیتور انعطاف‌پذیر **کور Xray**

## شروع سریع

1. [نصب](/fa/installation)
2. کلید موقت owner
3. ساخت اکانت owner در داشبورد
4. پیکربندی Xray — [استک Xray](/fa/protocols/xray)
5. در صورت نیاز IPsec — [L2TP و IKEv2](/fa/protocols/ipsec)

## جامعه و حمایت

- **GitHub:** [pooyahpx/HPXPANEL](https://github.com/pooyahpx/HPXPANEL)
- **dev by hpx:** [github.com/pooyahpx](https://github.com/pooyahpx)
