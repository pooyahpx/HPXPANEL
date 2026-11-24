"""Shared-Iran port uniqueness and peer-port merge helpers."""

from app.services.hpx_pulse.port_guard import find_iran_port_conflicts, merge_peer_forward_ports


class _Peer:
    def __init__(self, id, name, iran_public_ip, control_port, port_forwards):
        self.id = id
        self.name = name
        self.iran_public_ip = iran_public_ip
        self.control_port = control_port
        self.port_forwards = port_forwards


def test_no_conflict_when_ports_differ():
    peers = [_Peer(1, "a", "1.1.1.1", 50001, ["2082=127.0.0.1:2082"])]
    assert (
        find_iran_port_conflicts(
            iran_ip="1.1.1.1",
            control_port=50002,
            port_forwards=["443=127.0.0.1:443"],
            peers=peers,
        )
        == []
    )


def test_control_port_conflict():
    peers = [_Peer(1, "dadadshmjadid", "1.1.1.1", 57051, ["2082=127.0.0.1:2082"])]
    msgs = find_iran_port_conflicts(
        iran_ip="1.1.1.1",
        control_port=57051,
        port_forwards=["443=127.0.0.1:443"],
        peers=peers,
    )
    assert msgs and "57051" in msgs[0]
    assert "dadadshmjadid" in msgs[0]


def test_forward_port_conflict():
    peers = [_Peer(1, "other", "1.1.1.1", 50001, ["2082=127.0.0.1:2082"])]
    msgs = find_iran_port_conflicts(
        iran_ip="1.1.1.1",
        control_port=50002,
        port_forwards=["2082=127.0.0.1:2082"],
        peers=peers,
    )
    assert msgs and "2082" in msgs[0]


def test_exclude_self_on_update():
    peers = [_Peer(9, "self", "1.1.1.1", 57051, ["2082=127.0.0.1:2082"])]
    assert (
        find_iran_port_conflicts(
            iran_ip="1.1.1.1",
            control_port=57051,
            port_forwards=["2082=127.0.0.1:2082"],
            peers=peers,
            exclude_pulse_id=9,
        )
        == []
    )


def test_merge_peer_forward_ports_does_not_overwrite():
    peers = [
        _Peer(1, "a", "10.0.0.1", 1, ["2082=127.0.0.1:2082"]),
        _Peer(2, "b", "10.0.0.1", 2, ["443=127.0.0.1:443"]),
        _Peer(3, "c", "10.0.0.2", 3, ["8443=127.0.0.1:8443"]),
    ]
    ips, ports = merge_peer_forward_ports(peers, exclude_pulse_id=99)
    assert ips == {"10.0.0.1", "10.0.0.2"}
    assert ports["10.0.0.1"] == {2082, 443}
    assert ports["10.0.0.2"] == {8443}
