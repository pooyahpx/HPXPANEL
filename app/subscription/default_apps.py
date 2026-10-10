"""Built-in recommended client apps for the public subscription page.

Used as a fallback when Settings -> Subscription -> Applications is empty.
Mirrors the key apps from dashboard/src/features/subscriptions/components/default-applications-catalog.ts
"""

from app.models.settings import Application, DownloadLink, Language, Platform

_DOWNLOAD_LABELS: dict[Language, str] = {
    Language.EN: "Download",
    Language.FA: "دانلود",
    Language.RU: "Скачать",
    Language.ZH: "下载",
}

# (name, platform, icon, import_url, download_url, recommended, {lang: description})
_DEFAULT_APPS: tuple[tuple[str, Platform, str, str, str, bool, dict[Language, str]], ...] = (
    (
        "Streisand",
        Platform.IOS,
        "https://is1-ssl.mzstatic.com/image/thumb/Purple211/v4/1e/29/e0/1e29e04f-273b-9186-5f12-9bbe48c0fce2/AppIcon-0-0-1x_U007epad-0-0-0-1-0-85-220.png/460x0w.webp",
        "streisand://import/{url}",
        "https://apps.apple.com/us/app/streisand/id6450534064",
        True,
        {
            Language.EN: "Flexible proxy client with rule-based setup and many protocols (VLESS Reality, VMess, Trojan, Shadowsocks, Hysteria, TUIC, WireGuard).",
            Language.FA: "کلاینت پراکسی انعطاف‌پذیر با پشتیبانی از پروتکل‌های متعدد (VLESS Reality، VMess، Trojan، Shadowsocks، Hysteria، TUIC، WireGuard).",
            Language.RU: "Гибкий прокси-клиент с правилами и поддержкой множества протоколов.",
            Language.ZH: "灵活的代理客户端，支持多种协议与基于规则的配置。",
        },
    ),
    (
        "V2rayNG",
        Platform.ANDROID,
        "https://raw.githubusercontent.com/2dust/v2rayNG/refs/heads/master/V2rayNG/app/src/main/ic_launcher-web.png",
        "v2rayng://install-config?url={url}",
        "https://github.com/2dust/v2rayNG/releases/latest",
        True,
        {
            Language.EN: "A V2Ray client for Android devices.",
            Language.FA: "V2rayNG یک کلاینت V2Ray برای دستگاه‌های اندرویدی است.",
            Language.RU: "Клиент V2Ray для устройств Android.",
            Language.ZH: "适用于 Android 设备的 V2Ray 客户端。",
        },
    ),
    (
        "v2rayN",
        Platform.WINDOWS,
        "https://raw.githubusercontent.com/2dust/v2rayN/refs/heads/master/v2rayN/v2rayN.Desktop/v2rayN.png",
        "",
        "https://github.com/2dust/v2rayN/releases/latest",
        True,
        {
            Language.EN: "A Windows V2Ray client with GUI support.",
            Language.FA: "v2rayN یک کلاینت V2Ray برای ویندوز با پشتیبانی از رابط کاربری است.",
            Language.RU: "V2Ray клиент для Windows с графическим интерфейсом.",
            Language.ZH: "带有图形界面的 Windows V2Ray 客户端。",
        },
    ),
    (
        "V2Box",
        Platform.MACOS,
        "",
        "v2box://install-sub?url={url}",
        "https://apps.apple.com/us/app/v2box-v2ray-client/id6446814690",
        True,
        {
            Language.EN: "V2Ray client for macOS and iOS with subscription import.",
            Language.FA: "کلاینت V2Ray برای macOS و iOS با امکان وارد کردن اشتراک.",
            Language.RU: "Клиент V2Ray для macOS и iOS с импортом подписки.",
            Language.ZH: "支持订阅导入的 macOS / iOS V2Ray 客户端。",
        },
    ),
    (
        "FoXray",
        Platform.MACOS,
        "",
        "",
        "https://apps.apple.com/us/app/foxray/id6448898396",
        False,
        {
            Language.EN: "Alternative Xray-based client for macOS.",
            Language.FA: "کلاینت جایگزین مبتنی بر Xray برای macOS.",
            Language.RU: "Альтернативный клиент на базе Xray для macOS.",
            Language.ZH: "基于 Xray 的 macOS 备选客户端。",
        },
    ),
    (
        "Hiddify",
        Platform.ANDROID,
        "",
        "hiddify://import/{url}",
        "https://github.com/hiddify/hiddify-app/releases/latest",
        False,
        {
            Language.EN: "Multi-protocol client (Android, Windows, Linux, macOS) with one-tap subscription import.",
            Language.FA: "کلاینت چندپروتکلی (اندروید، ویندوز، لینوکس، macOS) با وارد کردن سریع اشتراک.",
            Language.RU: "Мультипротокольный клиент с быстрым импортом подписки.",
            Language.ZH: "多协议客户端，支持一键导入订阅。",
        },
    ),
)


def build_default_applications() -> list[Application]:
    """Return a fresh list of built-in applications (safe to mutate)."""
    apps: list[Application] = []
    for name, platform, icon, import_url, download_url, recommended, descriptions in _DEFAULT_APPS:
        apps.append(
            Application(
                name=name,
                icon_url=icon,
                import_url=import_url,
                description=dict(descriptions),
                recommended=recommended,
                # Fallback catalog should stay visible on the public page even when HWID is on.
                show_when_hwid_enabled=True,
                platform=platform,
                download_links=[
                    DownloadLink(name=label, url=download_url, language=lang)
                    for lang, label in _DOWNLOAD_LABELS.items()
                ],
            )
        )
    return apps
