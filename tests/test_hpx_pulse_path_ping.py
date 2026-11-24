"""Path-ping request/response models for Pulse live TCP/UDP samples."""

from datetime import UTC, datetime as dt

from app.models.hpx_pulse import HpxPulsePathPingRequest, HpxPulsePathPingResponse
from app.operation.hpx_pulse import (
    PATH_PING_QUEUED_TTL_SEC,
    _can_queue_command,
    _command_kind,
    _expire_path_ping_in_memory,
)


class _Pulse:
    def __init__(self, **kwargs):
        self.iran_agent_key_hash = kwargs.get("iran_agent_key_hash")
        self.abroad_agent_key_hash = kwargs.get("abroad_agent_key_hash")
        self.iran_agent_command = kwargs.get("iran_agent_command")
        self.abroad_agent_command = kwargs.get("abroad_agent_command")
        self.diag_report = kwargs.get("diag_report")


def test_path_ping_request_defaults():
    req = HpxPulsePathPingRequest()
    assert req.proto == "tcp"
    assert req.count == 4
    # Forward is default — control probes reset reverse/stealth tunnels.
    assert req.target == "forward"


def test_command_kind_path_ping():
    assert _command_kind("pp:t:4:f") == "path_ping"
    assert _command_kind("path-ping:tcp:4:forward") == "path_ping"
    assert _command_kind("leave") == "leave"
    assert _command_kind("restart") == "other"


def test_sync_cannot_clobber_path_ping():
    pulse = _Pulse(abroad_agent_key_hash="x", abroad_agent_command="pp:t:4:f")
    assert not _can_queue_command(pulse, "abroad", incoming="restart")
    assert not _can_queue_command(pulse, "abroad", incoming="diagnose")
    assert _can_queue_command(pulse, "abroad", incoming="pp:u:4:f")
    assert _can_queue_command(pulse, "abroad", incoming="leave")


def test_path_ping_queued_expires():
    stale_ts = int(dt.now(UTC).timestamp()) - PATH_PING_QUEUED_TTL_SEC - 5
    pulse = _Pulse(diag_report={"path_ping": {"status": "queued", "ts": stale_ts, "replies": []}})
    expired = _expire_path_ping_in_memory(pulse)
    assert expired["status"] == "error"
    assert "timed out" in expired["detail"]


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
