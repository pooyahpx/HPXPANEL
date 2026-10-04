"""Path-ping request/response models for Pulse live TCP/UDP samples."""

from app.models.hpx_pulse import HpxPulsePathPingRequest, HpxPulsePathPingResponse


def test_path_ping_request_defaults():
    req = HpxPulsePathPingRequest()
    assert req.proto == "tcp"
    assert req.count == 4
    assert req.target == "control"


def test_path_ping_compact_command_fits_legacy_column():
    """agent_command was String(16); compact pp:* must always fit before widen migration."""
    cases = [
        ("tcp", 4, "control"),
        ("udp", 8, "forward"),
        ("tcp", 20, "control"),
        ("udp", 20, "forward"),
    ]
    for proto, count, target in cases:
        proto_s = "t" if proto == "tcp" else "u"
        target_s = "c" if target == "control" else "f"
        cmd = f"pp:{proto_s}:{count}:{target_s}"
        assert len(cmd) <= 16, cmd


def test_path_ping_request_udp_forward():
    req = HpxPulsePathPingRequest(proto="udp", count=8, target="forward")
    assert req.proto == "udp"
    assert req.count == 8
    assert req.target == "forward"


def test_path_ping_response_shape():
    res = HpxPulsePathPingResponse(
        pulse_id=1,
        name="forest",
        queued=True,
        proto="tcp",
        count=4,
        target="control",
        port=50008,
        hint="sampling",
        path_ping={"status": "queued", "proto": "tcp", "replies": []},
    )
    assert res.queued is True
    assert res.path_ping["status"] == "queued"
