"""Curated HPX-Stealth host presets — Reality / Hysteria2 / fragment.

These are operator intents, not free-form cipher invention. Values are
battle-tested defaults the host modal can apply in one click.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class HostStealthPreset(BaseModel):
    id: str
    title: str
    title_fa: str
    intent: str = Field(description="mobile | hard | fast")
    stack: str = Field(description="reality | hysteria2 | fragment")
    description: str
    description_fa: str
    host_patch: dict


_PRESETS: list[HostStealthPreset] = [
    HostStealthPreset(
        id="stealth-reality-mobile",
        title="Reality · Mobile",
        title_fa="Reality · موبایل",
        intent="mobile",
        stack="reality",
        description="VLESS+Reality with chrome fingerprint and mild fragment for phones.",
        description_fa="VLESS+Reality با fingerprint کروم و fragment ملایم برای موبایل.",
        host_patch={
            "remark": "HPX Stealth Reality Mobile",
            "security": "inbound_default",
            "fingerprint": "chrome",
            "allowinsecure": False,
            "sni": ["www.microsoft.com"],
            "host": ["www.microsoft.com"],
            "path": "/",
            "fragment_settings": {
                "xray": {"packets": "tlshello", "length": "50-100", "interval": "10-20"},
                "sing_box": {"fragment": True, "fragment_fallback_delay": "500ms", "record_fragment": False},
            },
            "http_headers": {},
        },
    ),
    HostStealthPreset(
        id="stealth-reality-hard",
        title="Reality · Hard DPI",
        title_fa="Reality · DPI سخت",
        intent="hard",
        stack="reality",
        description="Aggressive Reality + stronger fragment split for harsh DPI.",
        description_fa="Reality تهاجمی با fragment قوی‌تر برای DPI سخت.",
        host_patch={
            "remark": "HPX Stealth Reality Hard",
            "security": "inbound_default",
            "fingerprint": "chrome",
            "allowinsecure": False,
            "sni": ["www.cloudflare.com"],
            "host": ["www.cloudflare.com"],
            "path": "/",
            "fragment_settings": {
                "xray": {"packets": "tlshello", "length": "10-20", "interval": "10-20"},
                "sing_box": {"fragment": True, "fragment_fallback_delay": "300ms", "record_fragment": True},
            },
            "noise_settings": {
                "xray": [
                    {
                        "type": "rand",
                        "packet": "10-30",
                        "delay": "10-20",
                        "apply_to": "ip",
                    }
                ]
            },
        },
    ),
    HostStealthPreset(
        id="stealth-fragment-fast",
        title="Fragment · Fast",
        title_fa="Fragment · سریع",
        intent="fast",
        stack="fragment",
        description="Lightweight TLS hello fragment — low CPU, good on clean-ish paths.",
        description_fa="Fragment سبک روی TLS hello — CPU کم، مناسب مسیر نسبتاً تمیز.",
        host_patch={
            "remark": "HPX Stealth Fragment Fast",
            "security": "tls",
            "fingerprint": "chrome",
            "allowinsecure": False,
            "alpn": ["h2", "http/1.1"],
            "fragment_settings": {
                "xray": {"packets": "tlshello", "length": "100-200", "interval": "1-5"},
                "sing_box": {"fragment": True, "fragment_fallback_delay": "200ms", "record_fragment": False},
            },
        },
    ),
    HostStealthPreset(
        id="stealth-hy2-hard",
        title="Hysteria2 · Hard",
        title_fa="Hysteria2 · سخت",
        intent="hard",
        stack="hysteria2",
        description="Hysteria2-oriented host defaults with TLS fingerprint and padding-friendly path.",
        description_fa="پیش‌فرض میزبان برای Hysteria2 با fingerprint TLS و path مناسب padding.",
        host_patch={
            "remark": "HPX Stealth Hysteria2 Hard",
            "security": "tls",
            "fingerprint": "firefox",
            "allowinsecure": False,
            "alpn": ["h3"],
            "sni": ["www.bing.com"],
            "path": "/hpx",
            "fragment_settings": {
                "xray": {"packets": "1-3", "length": "50-100", "interval": "10-20"},
            },
            "mux_settings": {
                "xray": {
                    "enabled": False,
                    "concurrency": None,
                    "xudp_concurrency": None,
                    "xudp_proxy_443": "reject",
                }
            },
        },
    ),
    HostStealthPreset(
        id="stealth-hy2-fast",
        title="Hysteria2 · Fast",
        title_fa="Hysteria2 · سریع",
        intent="fast",
        stack="hysteria2",
        description="Minimal Hysteria2 host patch — speed first, light fragment.",
        description_fa="پچ مینیمال Hysteria2 — اولویت سرعت، fragment سبک.",
        host_patch={
            "remark": "HPX Stealth Hysteria2 Fast",
            "security": "tls",
            "fingerprint": "chrome",
            "allowinsecure": False,
            "alpn": ["h3"],
            "sni": ["www.google.com"],
            "path": "/",
            "fragment_settings": None,
        },
    ),
    HostStealthPreset(
        id="stealth-fragment-mobile",
        title="Fragment · Mobile",
        title_fa="Fragment · موبایل",
        intent="mobile",
        stack="fragment",
        description="Balanced fragment for mobile clients behind carrier DPI.",
        description_fa="Fragment متعادل برای کلاینت موبایل پشت DPI اپراتور.",
        host_patch={
            "remark": "HPX Stealth Fragment Mobile",
            "security": "tls",
            "fingerprint": "chrome",
            "allowinsecure": False,
            "alpn": ["h2", "http/1.1"],
            "fragment_settings": {
                "xray": {"packets": "tlshello", "length": "50-100", "interval": "10-20"},
                "sing_box": {"fragment": True, "fragment_fallback_delay": "500ms", "record_fragment": False},
            },
        },
    ),
]


class HostStealthPresetsResponse(BaseModel):
    presets: list[HostStealthPreset]
    total: int


def list_host_stealth_presets(*, intent: str | None = None, stack: str | None = None) -> HostStealthPresetsResponse:
    rows = _PRESETS
    if intent:
        rows = [p for p in rows if p.intent == intent]
    if stack:
        rows = [p for p in rows if p.stack == stack]
    return HostStealthPresetsResponse(presets=rows, total=len(rows))


def get_host_stealth_preset(preset_id: str) -> HostStealthPreset | None:
    return next((p for p in _PRESETS if p.id == preset_id), None)
