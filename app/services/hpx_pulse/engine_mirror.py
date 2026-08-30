"""Cache and serve HPX tunnel engine binaries for Pulse agents (panel-side mirror)."""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

import aiohttp

logger = logging.getLogger(__name__)

_CODE_ROOT = Path(__file__).resolve().parents[3]
_VERSION_FILE = _CODE_ROOT / "scripts" / "hpx-tunnel-engine.version"
_INSTALL_SCRIPT = _CODE_ROOT / "scripts" / "hpx-tunnel-engine-install.sh"
_CACHE_DIR = Path(os.environ.get("HPX_DATA_DIR", "/var/lib/hpxpanel")) / "tunnel-engine"
_ENGINE_REPO = os.environ.get("HPX_TUNNEL_ENGINE_REPO", "pooyahpx/HPXPANEL")

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


def github_download_url(arch: str) -> str:
    tag = release_tag()
    name = asset_name(arch)
    return f"https://github.com/{_ENGINE_REPO}/releases/download/{tag}/{name}"


def cached_asset_path(arch: str) -> Path:
    return _CACHE_DIR / asset_name(arch)


def install_script_path() -> Path:
    return _INSTALL_SCRIPT


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


async def ensure_engine_cached(arch: str) -> Path:
    normalized = normalize_arch(arch)
    dest = cached_asset_path(normalized)
    if dest.is_file() and dest.stat().st_size > 0:
        return dest

    lock = _download_locks.setdefault(normalized, asyncio.Lock())
    async with lock:
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
