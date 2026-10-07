from app.services.hpx_pulse.config_linker import (
    forward_listen_ports,
    host_belongs_to_other_pulse,
    rewrite_host_addresses_to_iran,
    scan_hosts_for_pulse,
)


class _Host:
    def __init__(self, id, remark, address, port):
        self.id = id
        self.remark = remark
        self.address = address
        self.port = port


def test_forward_listen_ports():
    assert forward_listen_ports(["2088=127.0.0.1:2088", "2053=127.0.0.1:2053"]) == {2088, 2053}
    assert forward_listen_ports([]) == set()


def test_rewrite_does_not_steal_other_iran_ip():
    out = rewrite_host_addresses_to_iran(
        {"104.238.158.185", "85.133.243.112"},
        abroad_ip="104.238.158.185",
        iran_ip="185.218.139.145",
        protected_iran_ips={"85.133.243.112"},
    )
    assert "85.133.243.112" in out
    assert "185.218.139.145" in out
    assert "104.238.158.185" not in out


def test_rewrite_abroad_only_to_this_iran():
    out = rewrite_host_addresses_to_iran(
        {"104.238.158.185"},
        abroad_ip="104.238.158.185",
        iran_ip="185.218.139.145",
        protected_iran_ips={"85.133.243.112"},
    )
    assert out == {"185.218.139.145"}


def test_host_belongs_to_other_pulse_by_iran_ip():
    assert host_belongs_to_other_pulse(
        addresses=["85.133.243.112"],
        host_port=2053,
        my_iran_ip="185.218.139.145",
        my_forward_ports={2088},
        peer_iran_ips={"85.133.243.112"},
        peer_forward_ports={"85.133.243.112": {2053}},
    )


def test_host_belongs_to_other_pulse_by_port():
    assert host_belongs_to_other_pulse(
        addresses=["104.238.158.185"],
        host_port=2053,
        my_iran_ip="185.218.139.145",
        my_forward_ports={2088},
        peer_iran_ips={"85.133.243.112"},
        peer_forward_ports={"85.133.243.112": {2053}},
    )


def test_host_does_not_belong_when_port_matches_mine():
    assert not host_belongs_to_other_pulse(
        addresses=["104.238.158.185"],
        host_port=2088,
        my_iran_ip="185.218.139.145",
        my_forward_ports={2088},
        peer_iran_ips={"85.133.243.112"},
        peer_forward_ports={"85.133.243.112": {2053}},
    )


def test_scan_hosts_shared_abroad():
    hosts = [
        _Host(1, "a", {"104.238.158.185"}, 2053),
        _Host(2, "b", {"185.218.139.145"}, 2088),
    ]
    hits = scan_hosts_for_pulse(hosts, iran_ip="185.218.139.145", abroad_ip="104.238.158.185")
    issues = {h.host_id: h.issue for h in hits}
    assert issues[1] == "abroad_ip"
    assert issues[2] == "ok_iran"


def test_agent_script_has_multi_tunnel_isolation_guards():
    """Regression: ping purge / global MSS / shared Xray restart broke sibling tunnels."""
    from pathlib import Path

    script = Path("scripts/hpx-pulse-agent.sh").read_text(encoding="utf-8")
    assert "maybe_prune_orphan_configs" in script
    assert "NOT restarting Xray" in script
    assert "tcp_base_mss" not in script or "Do not set global tcp_base_mss" in script
    assert "siblings untouched" in script
    assert "multi-tunnel Sync race" in script
