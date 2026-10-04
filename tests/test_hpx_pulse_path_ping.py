"""Path-ping request/response models for Pulse live TCP/UDP samples."""

from app.models.hpx_pulse import HpxPulsePathPingRequest, HpxPulsePathPingResponse


def test_path_ping_request_defaults():
    req = HpxPulsePathPingRequest()
    assert req.proto == "tcp"
    assert req.count == 4
    assert req.target == "control"


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
