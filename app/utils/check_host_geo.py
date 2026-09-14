"""IP geolocation via check-host.net (HTML ip-info page)."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass

import aiohttp

_CACHE_TTL_SECONDS = 6 * 60 * 60
_cache: dict[str, tuple[float, "CheckHostIpInfo"]] = {}

_COUNTRY_ROW_RE = re.compile(
    r"Country</td>\s*<td[^>]*>.*?<strong>([^<]+)</strong>\s*\(([A-Z]{2})\)",
    re.IGNORECASE | re.DOTALL,
)
_CITY_ROW_RE = re.compile(
    r"City</td>\s*<td[^>]*>(.*?)</td>",
    re.IGNORECASE | re.DOTALL,
)
_ISP_ROW_RE = re.compile(
    r"ISP\s*/\s*Org</td>\s*<td[^>]*>(.*?)</td>",
    re.IGNORECASE | re.DOTALL,
)
_ASN_ROW_RE = re.compile(
    r"ASN</td>\s*<td[^>]*>(.*?)</td>",
    re.IGNORECASE | re.DOTALL,
)
_TAG_RE = re.compile(r"<[^>]+>")


@dataclass(frozen=True)
class CheckHostIpInfo:
    ip: str
    country: str | None
    country_code: str | None
    city: str | None
    isp: str | None
    asn: str | None
    source: str = "check-host.net"


def _clean_html_text(value: str | None) -> str | None:
    if not value:
        return None
    text = _TAG_RE.sub(" ", value)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def _parse_check_host_html(ip: str, html: str) -> CheckHostIpInfo | None:
    country = None
    country_code = None
    city = None
    isp = None
    asn = None

    for match in _COUNTRY_ROW_RE.finditer(html):
        country = _clean_html_text(match.group(1))
        country_code = match.group(2).upper()
        break

    for match in _CITY_ROW_RE.finditer(html):
        city = _clean_html_text(match.group(1))
        if city:
            break

    for match in _ISP_ROW_RE.finditer(html):
        isp = _clean_html_text(match.group(1))
        if isp:
            break

    for match in _ASN_ROW_RE.finditer(html):
        asn = _clean_html_text(match.group(1))
        if asn:
            break

    if not country_code and not isp:
        return None

    return CheckHostIpInfo(
        ip=ip,
        country=country,
        country_code=country_code,
        city=city,
        isp=isp,
        asn=asn,
    )


async def lookup_check_host_ip(host: str, *, force: bool = False) -> CheckHostIpInfo | None:
    """Resolve country / ISP for a public IP using check-host.net ip-info."""
    target = (host or "").strip()
    if not target:
        return None

    cached = _cache.get(target)
    now = time.time()
    if not force and cached and cached[0] > now:
        return cached[1]

    url = "https://check-host.net/ip-info"
    headers = {
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en",
        "User-Agent": "HPXPANEL/3.17 (+https://github.com/pooyahpx/HPXPANEL)",
    }

    try:
        timeout = aiohttp.ClientTimeout(total=12)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, params={"host": target}, headers=headers) as response:
                response.raise_for_status()
                html = await response.text()
                info = _parse_check_host_html(target, html)
    except Exception:
        return cached[1] if cached else None

    if info is None:
        return cached[1] if cached else None

    _cache[target] = (now + _CACHE_TTL_SECONDS, info)
    return info
