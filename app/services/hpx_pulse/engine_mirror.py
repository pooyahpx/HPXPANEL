"""Cache and serve HPX tunnel engine binaries for Pulse agents (panel-side mirror)."""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

import aiohttp

from app.lifecycle import on_startup

logger = logging.getLogger(__name__)

_CODE_ROOT = Path(__file__).resolve().parents[3]
_VERSION_FILE = _CODE_ROOT / "scripts" / "hpx-tunnel-engine.version"
_INSTALL_SCRIPT = _CODE_ROOT / "scripts" / "hpx-tunnel-engine-install.sh"
_AGENT_SCRIPT = _CODE_ROOT / "scripts" / "hpx-pulse-agent.sh"
_BUNDLED_DIR = _CODE_ROOT / "bundled" / "tunnel-engine"
_CACHE_DIR = Path(os.environ.get("HPX_DATA_DIR", "/var/lib/hpxpanel")) / "tunnel-engine"
_ENGINE_REPO = os.environ.get("HPX_TUNNEL_ENGINE_REPO", "pooyahpx/HPXPANEL")
_CHECKSUMS_NAME = "SHA256SUMS"

_ARCH_ASSETS = {
    "amd64": "hpx-tunnel-engine_linux_amd64.tar.gz",
    "arm64": "hpx-tunnel-engine_linux_arm64.tar.gz",
}

_download_locks: dict[str, asyncio.Lock] = {}


def normalize_arch(arch: str) -> str:
    value = arch.strip().lower()
    if value in {"x86_64", "amd64"}:
        return "amd64"
    if value in {"aarch64", "arm64"}:
        return "arm64"
    raise ValueError(f"unsupported architecture: {arch}")


def engine_version() -> str:
    if path := os.environ.get("HPX_TUNNEL_ENGINE_VERSION"):
        return path.removeprefix("v").strip()
    if _VERSION_FILE.is_file():
        return _VERSION_FILE.read_text(encoding="utf-8").strip().removeprefix("v")
    return "1.7.5"


def asset_name(arch: str) -> str:
    return _ARCH_ASSETS[normalize_arch(arch)]


def release_tag() -> str:
    return f"hpx-tunnel-engine-v{engine_version()}"


def agent_assets_base(panel_url: str | None) -> str | None:
    if not panel_url:
        return None
    return f"{panel_url.rstrip('/')}/api/hpx_pulse/agent"


def github_download_url(arch: str) -> str:
    tag = release_tag()
    name = asset_name(arch)
    return f"https://github.com/{_ENGINE_REPO}/releases/download/{tag}/{name}"


def github_checksums_url() -> str:
    tag = release_tag()
    return f"https://github.com/{_ENGINE_REPO}/releases/download/{tag}/{_CHECKSUMS_NAME}"


def bundled_asset_path(arch: str) -> Path | None:
    path = _BUNDLED_DIR / asset_name(arch)
    if path.is_file() and path.stat().st_size > 0:
        return path
    return None


def bundled_checksums_path() -> Path | None:
    path = _BUNDLED_DIR / _CHECKSUMS_NAME
    if path.is_file() and path.stat().st_size > 0:
        return path
    return None


def cached_asset_path(arch: str) -> Path:
    return _CACHE_DIR / asset_name(arch)


def cached_checksums_path() -> Path:
    return _CACHE_DIR / _CHECKSUMS_NAME


def install_script_path() -> Path:
    return _INSTALL_SCRIPT


def agent_script_path() -> Path:
    return _AGENT_SCRIPT


async def _download_to_path(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    timeout = aiohttp.ClientTimeout(total=600, connect=30)
    async with aiohttp.ClientSession(timeout=timeout) as session, session.get(url) as response:
        response.raise_for_status()
        with tmp.open("wb") as handle:
            async for chunk in response.content.iter_chunked(1024 * 256):
                handle.write(chunk)
    tmp.replace(dest)


async def ensure_checksums_cached() -> Path:
    bundled = bundled_checksums_path()
    if bundled is not None:
        return bundled

    dest = cached_checksums_path()
    if dest.is_file() and dest.stat().st_size > 0:
        return dest

    url = github_checksums_url()
    logger.info("Caching HPX tunnel engine checksums from %s", url)
    await _download_to_path(url, dest)
    return dest


async def ensure_engine_cached(arch: str) -> Path:
    normalized = normalize_arch(arch)
    bundled = bundled_asset_path(normalized)
    if bundled is not None:
        return bundled

    dest = cached_asset_path(normalized)
    if dest.is_file() and dest.stat().st_size > 0:
        return dest

    lock = _download_locks.setdefault(normalized, asyncio.Lock())
    async with lock:
        bundled = bundled_asset_path(normalized)
        if bundled is not None:
            return bundled
        if dest.is_file() and dest.stat().st_size > 0:
            return dest

        url = github_download_url(normalized)
        logger.info("Caching HPX tunnel engine %s from %s", normalized, url)
        try:
            await _download_to_path(url, dest)
        except Exception:
            if dest.is_file():
                dest.unlink(missing_ok=True)
            raise
        return dest


async def prewarm_engine_cache() -> None:
    """Panel startup: cache both arches so Iran agents never wait on GitHub."""
    for arch in ("amd64", "arm64"):
        try:
            await ensure_engine_cached(arch)
        except Exception as exc:
            logger.warning("HPX tunnel engine prewarm failed for %s: %s", arch, exc)
    try:
        await ensure_checksums_cached()
    except Exception as exc:
        logger.warning("HPX tunnel engine checksum prewarm failed: %s", exc)


@on_startup
async def _prewarm_hpx_tunnel_engine_cache() -> None:
    asyncio.create_task(prewarm_engine_cache())
