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
