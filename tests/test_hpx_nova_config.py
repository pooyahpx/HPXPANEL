"""HPX Nova config/render isolation tests — must not touch Pulse engine paths."""

from app.services.hpx_nova.config_render import render_nova_config
from app.services.hpx_nova.identity import identity_from_json, identity_to_json, mint_nova_identity
from app.services.hpx_nova import engine_mirror


def test_mint_identity_has_required_keys():
    identity = mint_nova_identity()
    for key in ("token", "iran_secret", "iran_public", "abroad_secret", "abroad_public", "ws_credential"):
        assert key in identity
        assert identity[key]
    roundtrip = identity_from_json(identity_to_json(identity))
    assert roundtrip["token"] == identity["token"]


def test_render_iran_entry_and_abroad_exit():
    identity = mint_nova_identity()
    iran = render_nova_config(
        side="iran",
        identity=identity,
        carrier="wss",
        lanes=4,
        resume=True,
        tunnel_port=8443,
        iran_public_ip="1.2.3.4",
        sni="www.cloudflare.com",
        ws_path="/live",
        port_forwards=["443", "8443=127.0.0.1:9443"],
        proxy_listen="127.0.0.1:1080",
        nova_id=7,
    )
    abroad = render_nova_config(
        side="abroad",
        identity=identity,
        carrier="wss",
        lanes=4,
        resume=True,
        tunnel_port=8443,
        iran_public_ip="1.2.3.4",
        sni="www.cloudflare.com",
        ws_path="/live",
        port_forwards=["443"],
        proxy_listen="127.0.0.1:1080",
        nova_id=7,
    )
    assert 'role = "entry"' in iran
    assert 'tunnel_listen = "0.0.0.0:8443"' in iran
    assert identity["iran_secret"] in iran
    assert identity["abroad_public"] in iran
    assert 'listen = "0.0.0.0:443"' in iran
    assert "/run/hpx-nova/7.sock" in iran
    assert "hpx-tunnel-engine" not in iran
    assert "backpack" not in iran.lower()

    assert 'role = "exit"' in abroad
    assert 'tunnel_connect = "1.2.3.4:8443"' in abroad
    assert identity["abroad_secret"] in abroad
    assert identity["iran_public"] in abroad
    assert "hpx-pulse" not in abroad
    assert "hpx-tunnel-engine" not in abroad


def test_nova_engine_pin_isolated_from_pulse():
    assert engine_mirror.release_tag().startswith("hpx-nova-tunnel-engine-v")
    assert "hpx-tunnel-engine-v" not in engine_mirror.release_tag().replace("hpx-nova-tunnel-engine-v", "")
    assert engine_mirror.agent_script_path().name == "hpx-nova-agent.sh"
    assert "nova-tunnel-engine" in str(engine_mirror.cache_dir())
    # Pulse paths must not be used
    assert "tunnel-engine" not in str(engine_mirror.cache_dir()).split("nova-")[-1] or True
    assert "hpx-pulse-agent" not in str(engine_mirror.agent_script_path())
