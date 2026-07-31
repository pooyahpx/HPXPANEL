---
title: Стек Xray
---

# Стек Xray

<div class="callout-new">

**Сердце HPXPANEL — Xray-core.** Большая часть флота живёт здесь: гибкие протоколы, REALITY / TLS, multi-inbound и подписки, которые понимают все клиенты.

</div>

## Протоколы

- **VLESS** — лёгкий современный протокол, идеален с REALITY
- **VMess** — классика с широкой совместимостью
- **Trojan** — TLS-подобный профиль
- **Shadowsocks** — простой и проверенный

## Слои

TLS · **REALITY** · multi-inbound · multi-protocol на одного пользователя

## Workflow

1. Создать/править **Xray core**
2. Хосты / inbounds
3. Включить протоколы на пользователе
4. Отдать **subscription** (V2Ray / Clash / ClashMeta)
5. Смотреть usage и статистику

Рядом можно добавить WireGuard / Hysteria2 или L2TP / IKEv2 и закрыть абьюз через **IP Limiter**.
