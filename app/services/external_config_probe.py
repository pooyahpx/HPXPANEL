"""TCP ping + light download probe for mother/external share links."""

from __future__ import annotations

import asyncio
import ssl
import time
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.services.copilot.proxy_uri import ProxyUriParseError, parse_proxy_link


class ExternalConfigProbeRequest(BaseModel):
    link: str = Field(min_length=8, max_length=8192)
    mode: Literal["ping", "speed", "both"] = "both"
    samples: int = Field(default=5, ge=1, le=20)


class ExternalConfigProbeResponse(BaseModel):
    ok: bool
    protocol: str | None = None
    host: str | None = None
    port: int | None = None
    sni: str | None = None
    remark: str | None = None
    ping: dict[str, Any] | None = None
    speed: dict[str, Any] | None = None
    error: str | None = None


async def _tcp_connect_ms(host: str, port: int, timeout: float) -> float | None:
    try:
        t0 = time.perf_counter()
        reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=timeout)
        ms = (time.perf_counter() - t0) * 1000.0
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        del reader
        return ms
    except Exception:
        return None


async def probe_tcp_ping(host: str, port: int, *, samples: int = 5, timeout: float = 2.5) -> dict[str, Any]:
    results: list[float] = []
    for _ in range(samples):
        ms = await _tcp_connect_ms(host, port, timeout)
        if ms is not None:
            results.append(ms)
        await asyncio.sleep(0.05)
    if not results:
        return {"ok": False, "samples": samples, "loss_pct": 100.0, "avg_ms": None, "min_ms": None, "max_ms": None}
    loss = max(0.0, (samples - len(results)) / samples * 100.0)
    return {
        "ok": True,
        "samples": samples,
        "success": len(results),
        "loss_pct": round(loss, 1),
        "avg_ms": round(sum(results) / len(results), 2),
        "min_ms": round(min(results), 2),
        "max_ms": round(max(results), 2),
    }


async def probe_download_speed(
    *,
    host: str,
    port: int,
    sni: str | None,
    timeout: float = 12.0,
    nbytes: int = 750_000,
) -> dict[str, Any]:
    """Best-effort path speed: HTTPS download against SNI/host (front), else TCP warm connect."""
    target_host = (sni or host or "").strip()
    if not target_host:
        return {"ok": False, "error": "no host/sni for speed probe"}

    # Prefer Cloudflare micro download when SNI looks like a CDN front; otherwise hit the SNI host.
    url = f"https://speed.cloudflare.com/__down?bytes={nbytes}"
    if sni and "cloudflare" not in sni.lower() and "google" not in sni.lower():
        url = f"https://{target_host}/"

    try:
        # stdlib-only HTTPS GET via asyncio.to_thread to keep deps light
        def _download() -> tuple[int, float]:
            import urllib.request

            ctx = ssl.create_default_context()
            req = urllib.request.Request(url, headers={"User-Agent": "HPXPANEL-external-probe/1.0"})
            t0 = time.perf_counter()
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                data = resp.read(nbytes)
            elapsed = max(time.perf_counter() - t0, 1e-6)
            return len(data), elapsed

        size, elapsed = await asyncio.wait_for(asyncio.to_thread(_download), timeout=timeout + 1)
        mbps = (size * 8) / elapsed / 1_000_000
        return {
            "ok": True,
            "bytes": size,
            "elapsed_s": round(elapsed, 3),
            "mbps": round(mbps, 2),
            "target": url.split("?", 1)[0],
            "note": "Front/path download from panel (not full VLESS handshake)",
        }
    except Exception as exc:
        # Fallback: TCP connect quality to the node itself
        ms = await _tcp_connect_ms(host, port, min(timeout, 3.0))
        if ms is None:
            return {"ok": False, "error": f"speed probe failed: {exc}"}
        return {
            "ok": True,
            "bytes": 0,
            "elapsed_s": round(ms / 1000.0, 3),
            "mbps": None,
            "tcp_connect_ms": round(ms, 2),
            "target": f"{host}:{port}",
            "note": f"HTTPS download failed ({exc}); reporting TCP connect only",
        }


async def probe_external_config(model: ExternalConfigProbeRequest) -> ExternalConfigProbeResponse:
    try:
        parsed = parse_proxy_link(model.link.strip())
    except ProxyUriParseError as exc:
        return ExternalConfigProbeResponse(ok=False, error=str(exc))
    except Exception as exc:
        return ExternalConfigProbeResponse(ok=False, error=f"parse failed: {exc}")

    host = parsed.address
    port = int(parsed.port)
    resp = ExternalConfigProbeResponse(
        ok=True,
        protocol=parsed.protocol,
        host=host,
        port=port,
        sni=parsed.sni,
        remark=parsed.remark or None,
    )

    if model.mode in {"ping", "both"}:
        resp.ping = await probe_tcp_ping(host, port, samples=model.samples)

    if model.mode in {"speed", "both"}:
        resp.speed = await probe_download_speed(host=host, port=port, sni=parsed.sni)

    if model.mode == "ping" and resp.ping and not resp.ping.get("ok"):
        resp.ok = False
        resp.error = "host unreachable"
    if model.mode == "speed" and resp.speed and not resp.speed.get("ok"):
        resp.ok = False
        resp.error = resp.speed.get("error") or "speed probe failed"

    return resp
