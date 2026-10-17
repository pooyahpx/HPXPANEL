"""Built-in recommended client apps for the public subscription page.

Used as a fallback when Settings -> Subscription -> Applications is empty.

Only real, publicly reachable download pages are listed (App Store / Google Play /
GitHub releases / official sites). ``import_url`` is only set where the client documents a
one-tap deep link that accepts the raw subscription URL via ``{url}``.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.models.settings import Application, DownloadLink, Language, Platform

_L = Language


def _desc(en: str, fa: str, ru: str, zh: str) -> dict[Language, str]:
    return {_L.EN: en, _L.FA: fa, _L.RU: ru, _L.ZH: zh}


# Short, accurate descriptions shared by every platform build of an app.
_DESCRIPTIONS: dict[str, dict[Language, str]] = {
    "streisand": _desc(
        "Rule-based iOS client with VLESS Reality, VMess, Trojan, Shadowsocks, Hysteria and TUIC.",
        "کلاینت قانون‌محور iOS با پشتیبانی از VLESS Reality، VMess، Trojan، Shadowsocks، Hysteria و TUIC.",
        "Клиент для iOS с правилами маршрутизации: VLESS Reality, VMess, Trojan, Shadowsocks, Hysteria, TUIC.",
        "基于规则的 iOS 客户端，支持 VLESS Reality、VMess、Trojan、Shadowsocks、Hysteria、TUIC。",
    ),
    "v2box": _desc(
        "Simple V2Ray client for iPhone, iPad and Mac with one-tap subscription import.",
        "کلاینت ساده V2Ray برای iPhone، iPad و Mac با افزودن یک‌لمسی اشتراک.",
        "Простой клиент V2Ray для iPhone, iPad и Mac с импортом подписки в одно касание.",
        "适用于 iPhone、iPad 和 Mac 的简洁 V2Ray 客户端，支持一键导入订阅。",
    ),
    "shadowrocket": _desc(
        "Popular paid iOS/macOS proxy client. Paste the subscription link under Subscribe.",
        "کلاینت پرطرفدار و پولی iOS/macOS. لینک اشتراک را در بخش Subscribe وارد کنید.",
        "Популярный платный клиент для iOS/macOS. Вставьте ссылку подписки в разделе Subscribe.",
        "热门付费 iOS/macOS 代理客户端，在 Subscribe 中粘贴订阅链接即可。",
    ),
    "happ": _desc(
        "Clean proxy client with subscription auto-update and one-tap import.",
        "کلاینت پراکسی ساده با به‌روزرسانی خودکار اشتراک و افزودن یک‌لمسی.",
        "Удобный прокси-клиент с автообновлением подписки и импортом в одно касание.",
        "简洁的代理客户端，支持订阅自动更新与一键导入。",
    ),
    "hiddify": _desc(
        "Multi-platform, multi-protocol client with auto-select and one-tap subscription import.",
        "کلاینت چندسکویی و چندپروتکلی با انتخاب خودکار بهترین سرور و افزودن یک‌لمسی اشتراک.",
        "Мультиплатформенный мультипротокольный клиент с автовыбором и быстрым импортом подписки.",
        "跨平台多协议客户端，支持自动选择节点与一键导入订阅。",
    ),
    "v2rayng": _desc(
        "The reference open-source V2Ray / Xray client for Android.",
        "کلاینت متن‌باز و مرجع V2Ray / Xray برای اندروید.",
        "Эталонный клиент V2Ray / Xray с открытым кодом для Android.",
        "Android 上的开源 V2Ray / Xray 参考客户端。",
    ),
    "v2raytun": _desc(
        "Lightweight Android client with quick subscription import.",
        "کلاینت سبک اندروید با افزودن سریع اشتراک.",
        "Лёгкий клиент для Android с быстрым импортом подписки.",
        "轻量级 Android 客户端，支持快速导入订阅。",
    ),
    "v2rayn": _desc(
        "Open-source Windows GUI client for Xray / sing-box. Add the subscription under Subscription settings.",
        "کلاینت گرافیکی و متن‌باز ویندوز برای Xray / sing-box. اشتراک را در بخش Subscription اضافه کنید.",
        "Графический клиент для Windows (Xray / sing-box) с открытым кодом. Добавьте подписку в разделе Subscription.",
        "开源 Windows 图形客户端（Xray / sing-box），在 Subscription 设置中添加订阅。",
    ),
    "v2raya": _desc(
        "Web-UI based V2Ray / Xray client for Linux, with transparent proxy support.",
        "کلاینت تحت وب V2Ray / Xray برای لینوکس با پشتیبانی از پروکسی شفاف.",
        "Веб-клиент V2Ray / Xray для Linux с поддержкой прозрачного прокси.",
        "基于 Web 界面的 Linux V2Ray / Xray 客户端，支持透明代理。",
    ),
}


@dataclass(frozen=True)
class _AppSpec:
    key: str
    name: str
    platform: Platform
    links: tuple[tuple[str, str], ...]  # (label, url); first one is the primary download
    import_url: str = ""
    icon: str = ""
    recommended: bool = False


_IOS = Platform.IOS
_ANDROID = Platform.ANDROID
_WINDOWS = Platform.WINDOWS
_MACOS = Platform.MACOS
_LINUX = Platform.LINUX

_HIDDIFY_GH = ("GitHub", "https://github.com/hiddify/hiddify-app/releases/latest")
_HIDDIFY_ICON = "https://raw.githubusercontent.com/hiddify/hiddify-app/main/assets/images/source/ic_launcher_border.png"
_HAPP_ICON = "https://is1-ssl.mzstatic.com/image/thumb/Purple211/v4/91/6b/00/916b0085-d7d9-1791-c94f-5f6adb9a3d37/AppIcon-0-0-1x_U007epad-0-0-0-1-0-0-85-220.png/256x256bb.jpg"
_V2BOX_ICON = "https://is1-ssl.mzstatic.com/image/thumb/Purple211/v4/73/e5/4f/73e54f12-2038-fa5f-9220-b6f522c3fdcc/V2BoxIcon-0-0-1x_U007epad-0-1-85-220.png/256x256bb.jpg"
_STREISAND_ICON = "https://is1-ssl.mzstatic.com/image/thumb/Purple221/v4/0b/cd/a2/0bcda234-4997-1fce-731b-96bd7d36c773/AppIcon-0-0-1x_U007epad-0-0-0-1-0-85-220.png/256x256bb.jpg"
_SHADOWROCKET_ICON = "https://is1-ssl.mzstatic.com/image/thumb/Purple211/v4/64/24/2d/64242de2-a763-914f-c686-8777445b83a3/AppIcon-0-0-1x_U007epad-0-1-0-sRGB-85-220.png/256x256bb.jpg"
_HIDDIFY_IOS_ICON = "https://is1-ssl.mzstatic.com/image/thumb/Purple211/v4/70/5e/2f/705e2fce-cacd-28c0-05bb-946667dbc03a/AppIcon-0-0-1x_U007epad-0-1-85-220.png/256x256bb.jpg"

_V2BOX_STORE = ("App Store", "https://apps.apple.com/us/app/v2box-v2ray-client/id6446814690")
_HAPP_STORE = ("App Store", "https://apps.apple.com/us/app/happ-proxy-utility/id6504287215")
_HIDDIFY_PLAY = ("Google Play", "https://play.google.com/store/apps/details?id=app.hiddify.com")

# Order matters: grouped by platform, recommended client first within each platform.
_DEFAULT_APPS: tuple[_AppSpec, ...] = (
    # ---- iOS
    _AppSpec(
        "streisand",
        "Streisand",
        _IOS,
        (("App Store", "https://apps.apple.com/us/app/streisand/id6450534064"),),
        import_url="streisand://import/{url}",
        icon=_STREISAND_ICON,
        recommended=True,
    ),
    _AppSpec("v2box", "V2Box", _IOS, (_V2BOX_STORE,), import_url="v2box://install-sub?url={url}", icon=_V2BOX_ICON),
    _AppSpec(
        "shadowrocket",
        "Shadowrocket",
        _IOS,
        (("App Store", "https://apps.apple.com/us/app/shadowrocket/id932747118"),),
        icon=_SHADOWROCKET_ICON,
    ),
    _AppSpec("happ", "Happ", _IOS, (_HAPP_STORE,), import_url="happ://add/{url}", icon=_HAPP_ICON),
    _AppSpec(
        "hiddify",
        "Hiddify",
        _IOS,
        (("App Store", "https://apps.apple.com/us/app/hiddify-proxy-vpn/id6596777532"),),
        import_url="hiddify://import/{url}",
        icon=_HIDDIFY_IOS_ICON,
    ),
    # ---- Android
    _AppSpec(
        "v2rayng",
        "v2rayNG",
        _ANDROID,
        (("GitHub", "https://github.com/2dust/v2rayNG/releases/latest"),),
        import_url="v2rayng://install-config?url={url}",
        icon="https://raw.githubusercontent.com/2dust/v2rayNG/refs/heads/master/V2rayNG/app/src/main/ic_launcher-web.png",
        recommended=True,
    ),
    _AppSpec(
        "hiddify",
        "Hiddify",
        _ANDROID,
        (_HIDDIFY_PLAY, _HIDDIFY_GH),
        import_url="hiddify://import/{url}",
        icon=_HIDDIFY_ICON,
    ),
    _AppSpec(
        "v2raytun",
        "v2rayTun",
        _ANDROID,
        (("Google Play", "https://play.google.com/store/apps/details?id=com.v2raytun.android"),),
        import_url="v2raytun://import/{url}",
    ),
    _AppSpec(
        "happ",
        "Happ",
        _ANDROID,
        (("Google Play", "https://play.google.com/store/apps/details?id=com.happproxy"),),
        import_url="happ://add/{url}",
        icon=_HAPP_ICON,
    ),
    # ---- Windows
    _AppSpec(
        "v2rayn",
        "v2rayN",
        _WINDOWS,
        (("GitHub", "https://github.com/2dust/v2rayN/releases/latest"),),
        icon="https://raw.githubusercontent.com/2dust/v2rayN/refs/heads/master/v2rayN/v2rayN.Desktop/v2rayN.png",
        recommended=True,
    ),
    _AppSpec("hiddify", "Hiddify", _WINDOWS, (_HIDDIFY_GH,), import_url="hiddify://import/{url}", icon=_HIDDIFY_ICON),
    # ---- macOS
    _AppSpec(
        "v2box",
        "V2Box",
        _MACOS,
        (_V2BOX_STORE,),
        import_url="v2box://install-sub?url={url}",
        icon=_V2BOX_ICON,
        recommended=True,
    ),
    _AppSpec("hiddify", "Hiddify", _MACOS, (_HIDDIFY_GH,), import_url="hiddify://import/{url}", icon=_HIDDIFY_ICON),
    _AppSpec("happ", "Happ", _MACOS, (_HAPP_STORE,), import_url="happ://add/{url}", icon=_HAPP_ICON),
    # ---- Linux
    _AppSpec(
        "hiddify",
        "Hiddify",
        _LINUX,
        (_HIDDIFY_GH,),
        import_url="hiddify://import/{url}",
        icon=_HIDDIFY_ICON,
        recommended=True,
    ),
    _AppSpec(
        "v2raya",
        "v2rayA",
        _LINUX,
        (
            ("GitHub", "https://github.com/v2rayA/v2rayA/releases/latest"),
            ("Website", "https://v2raya.org/"),
        ),
        icon="https://raw.githubusercontent.com/v2rayA/v2rayA/main/gui/public/img/icons/android-chrome-192x192.png",
    ),
)


def build_default_applications() -> list[Application]:
    """Return a fresh list of built-in applications (safe to mutate)."""
    apps: list[Application] = []
    for spec in _DEFAULT_APPS:
        apps.append(
            Application(
                name=spec.name,
                icon_url=spec.icon,
                import_url=spec.import_url,
                description=dict(_DESCRIPTIONS[spec.key]),
                recommended=spec.recommended,
                # Fallback catalog should stay visible on the public page even when HWID is on.
                show_when_hwid_enabled=True,
                platform=spec.platform,
                download_links=[
                    DownloadLink(name=label, url=url, language=lang) for lang in Language for label, url in spec.links
                ],
            )
        )
    return apps
