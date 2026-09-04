import hashlib

import pytest

from app.services.hpx_pulse import engine_mirror


def test_normalize_arch_aliases():
    assert engine_mirror.normalize_arch("amd64") == "amd64"
    assert engine_mirror.normalize_arch("x86_64") == "amd64"
    assert engine_mirror.normalize_arch("arm64") == "arm64"
    assert engine_mirror.normalize_arch("aarch64") == "arm64"


def test_agent_assets_base():
    assert engine_mirror.agent_assets_base("https://panel.example.com") == (
        "https://panel.example.com/api/hpx_pulse/agent"
    )
    assert engine_mirror.agent_assets_base(None) is None


def test_asset_name_and_release_tag():
    assert engine_mirror.asset_name("amd64") == "hpx-tunnel-engine_linux_amd64.tar.gz"
    assert engine_mirror.release_tag().startswith("hpx-tunnel-engine-v")


def test_install_and_agent_script_paths_exist():
    assert engine_mirror.install_script_path().is_file()
    assert engine_mirror.agent_script_path().is_file()


@pytest.mark.asyncio
async def test_verify_asset_accepts_valid_checksum(tmp_path):
    asset = tmp_path / engine_mirror.asset_name("amd64")
    asset.write_bytes(b"valid engine")
    checksum = hashlib.sha256(asset.read_bytes()).hexdigest()
    checksums = tmp_path / "SHA256SUMS"
    checksums.write_text(f"{checksum}  {asset.name}\n", encoding="utf-8")

    await engine_mirror.verify_asset(asset, checksums, asset.name)

    assert asset.is_file()


@pytest.mark.asyncio
async def test_verify_asset_deletes_checksum_mismatch(tmp_path):
    asset = tmp_path / engine_mirror.asset_name("amd64")
    asset.write_bytes(b"corrupt engine")
    checksums = tmp_path / "SHA256SUMS"
    checksums.write_text(f"{'0' * 64}  {asset.name}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="SHA256 mismatch"):
        await engine_mirror.verify_asset(asset, checksums, asset.name)

    assert not asset.exists()


@pytest.mark.asyncio
async def test_verify_asset_deletes_asset_when_checksum_missing(tmp_path):
    asset = tmp_path / engine_mirror.asset_name("arm64")
    asset.write_bytes(b"unverifiable engine")
    checksums = tmp_path / "SHA256SUMS"
    checksums.write_text(f"{'0' * 64}  other.tar.gz\n", encoding="utf-8")

    with pytest.raises(ValueError, match="missing SHA256 checksum"):
        await engine_mirror.verify_asset(asset, checksums, asset.name)

    assert not asset.exists()
