"""Mirror / pin HPX NOVA TUNNEL ENGINE binaries (isolated from Pulse engine_mirror)."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

from app.utils.logger import get_logger

logger = get_logger("hpx-nova-engine")

_CODE_ROOT = Path(__file__).resolve().parents[3]
_VERSION_FILE = _CODE_ROOT / "scripts" / "hpx-nova-tunnel-engine.version"
_INSTALL_SCRIPT = _CODE_ROOT / "scripts" / "hpx-nova-tunnel-engine-install.sh"
_AGENT_SCRIPT = _CODE_ROOT / "scripts" / "hpx-nova-agent.sh"
_BUNDLED_DIR = _CODE_ROOT / "bundled" / "nova-tunnel-engine"
_CACHE_DIR = Path(os.environ.get("HPX_DATA_DIR", "/var/lib/hpxpanel")) / "nova-tunnel-engine"

_ARCH_ASSETS = {
    "amd64": "hpx-nova-tunnel-engine_linux_amd64.tar.gz",
    "arm64": "hpx-nova-tunnel-engine_linux_arm64.tar.gz",
}


def engine_version() -> str:
    override = (os.environ.get("HPX_NOVA_TUNNEL_ENGINE_VERSION") or "").strip()
    if override:
        return override.lstrip("v")
    if _VERSION_FILE.is_file():
        return _VERSION_FILE.read_text(encoding="utf-8").strip().lstrip("v") or "0.1.0"
    return "0.1.0"


def release_tag() -> str:
    return f"hpx-nova-tunnel-engine-v{engine_version()}"


def install_script_path() -> Path:
    return _INSTALL_SCRIPT


def agent_script_path() -> Path:
    return _AGENT_SCRIPT


def normalize_arch(arch: str) -> str:
    raw = (arch or "").strip().lower()
    if raw in {"amd64", "x86_64", "x64"}:
        return "amd64"
    if raw in {"arm64", "aarch64"}:
        return "arm64"
    raise ValueError(f"unsupported arch: {arch}")


def agent_assets_base(panel_url: str) -> str:
    return f"{panel_url.rstrip('/')}/api/hpx_nova/agent"


def github_asset_url(arch: str) -> str:
    repo = (os.environ.get("HPX_NOVA_ENGINE_REPO") or "pooyahpx/HPXPANEL").strip()
    asset = _ARCH_ASSETS[normalize_arch(arch)]
    return f"https://github.com/{repo}/releases/download/{release_tag()}/{asset}"


def cache_dir() -> Path:
    path = _CACHE_DIR / release_tag()
    path.mkdir(parents=True, exist_ok=True)
    return path


async def ensure_checksums_cached() -> Path:
    import httpx

    dest = cache_dir() / "SHA256SUMS"
    if dest.is_file():
        return dest
    bundled = _BUNDLED_DIR / release_tag() / "SHA256SUMS"
    if bundled.is_file():
        dest.write_bytes(bundled.read_bytes())
        return dest
    repo = (os.environ.get("HPX_NOVA_ENGINE_REPO") or "pooyahpx/HPXPANEL").strip()
    url = f"https://github.com/{repo}/releases/download/{release_tag()}/SHA256SUMS"
    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        dest.write_bytes(resp.content)
    return dest


async def ensure_engine_cached(arch: str) -> Path:
    import httpx

    normalized = normalize_arch(arch)
    asset = _ARCH_ASSETS[normalized]
    dest = cache_dir() / asset
    if dest.is_file():
        return dest
    bundled = _BUNDLED_DIR / release_tag() / asset
    if bundled.is_file():
        dest.write_bytes(bundled.read_bytes())
        return dest
    url = github_asset_url(normalized)
    logger.info("Caching HPX Nova tunnel engine %s from %s", normalized, url)
    async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        dest.write_bytes(resp.content)
    sums = await ensure_checksums_cached()
    expected = _sha_from_sums(sums.read_text(encoding="utf-8"), asset)
    if expected:
        digest = hashlib.sha256(dest.read_bytes()).hexdigest()
        if digest.lower() != expected.lower():
            dest.unlink(missing_ok=True)
            raise RuntimeError(f"Nova engine checksum mismatch for {asset}")
    return dest


def _sha_from_sums(text: str, asset: str) -> str | None:
    for line in text.splitlines():
        parts = line.strip().split()
        if len(parts) >= 2 and parts[-1].endswith(asset):
            return parts[0]
    return None
