from app.operation.hpx_pulse import (
    _build_join_command_github,
    _build_join_command_panel,
    _url_with_host,
)


def test_url_with_host_keeps_non_default_port():
    assert _url_with_host("https://pnl.example.com:8443", "1.2.3.4") == "https://1.2.3.4:8443"


def test_url_with_host_omits_default_https_port():
    assert _url_with_host("https://pnl.example.com", "1.2.3.4") == "https://1.2.3.4"


def test_iran_github_join_includes_insecure_and_prefer_github():
    cmd = _build_join_command_github(
        "https://1.2.3.4",
        "hpxpi_token",
        "iran",
        insecure=True,
    )
    assert "HPX_PREFER_GITHUB=1" in cmd
    assert "--panel-url https://1.2.3.4 --side iran --insecure" in cmd
    assert "hpx-pulse-agent.sh" in cmd


def test_abroad_panel_join_has_no_insecure_by_default():
    cmd = _build_join_command_panel("https://pnl.example.com", "hpxpa_token", "abroad")
    assert "--side abroad" in cmd
    assert "--insecure" not in cmd
    assert "/api/hpx_pulse/agent/hpx-pulse-agent.sh" in cmd
