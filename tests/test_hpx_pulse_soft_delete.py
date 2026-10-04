"""Soft-delete + orphan cleanup helpers for HPX Pulse."""

from types import SimpleNamespace

from app.operation.hpx_pulse import PENDING_DELETE_MARKER, _is_pending_delete


def test_pending_delete_marker():
    assert _is_pending_delete(SimpleNamespace(message=f"{PENDING_DELETE_MARKER} agents uninstalling"))
    assert not _is_pending_delete(SimpleNamespace(message="running ok"))
    assert not _is_pending_delete(SimpleNamespace(message=None))
