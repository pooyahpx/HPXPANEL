"""Accumulate HPX Pulse interface counters into lifetime totals + timed samples."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime as dt, timedelta as td

from app.models.hpx_pulse import PulseUsageShareItem, PulseUsageShareResponse

ABROAD_PREFER_SECONDS = 120
SAMPLE_BUCKET_MINUTES = 10


@dataclass(frozen=True)
class TrafficDelta:
    uplink: int = 0
    downlink: int = 0


def floor_sample_bucket(when: dt, *, minutes: int = SAMPLE_BUCKET_MINUTES) -> dt:
    """Floor a timestamp to the start of an N-minute usage bucket (UTC-aware)."""
    if when.tzinfo is None:
        when = when.replace(tzinfo=UTC)
    else:
        when = when.astimezone(UTC)
    minute = (when.minute // minutes) * minutes
    return when.replace(minute=minute, second=0, microsecond=0)


def should_accept_traffic_side(
    *,
    side: str,
    abroad_last_seen: dt | None,
    now: dt | None = None,
) -> bool:
    """Prefer abroad counters when that agent is freshly online; else accept either side."""
    if side != "iran":
        return True
    if abroad_last_seen is None:
        return True
    now = now or dt.now(UTC)
    if abroad_last_seen.tzinfo is None:
        abroad_last_seen = abroad_last_seen.replace(tzinfo=UTC)
    return (now - abroad_last_seen).total_seconds() >= ABROAD_PREFER_SECONDS


def compute_counter_delta(
    *,
    current_rx: int,
    current_tx: int,
    last_rx: int | None,
    last_tx: int | None,
    same_side: bool,
) -> TrafficDelta:
    """
    Turn absolute iface counters into uplink(tx)/downlink(rx) deltas.

    Counter resets (reboot / reconnect) yield a zero delta and a fresh baseline.
    """
    if not same_side or last_rx is None or last_tx is None:
        return TrafficDelta()
    d_rx = int(current_rx) - int(last_rx)
    d_tx = int(current_tx) - int(last_tx)
    if d_rx < 0 or d_tx < 0:
        return TrafficDelta()
    return TrafficDelta(uplink=d_tx, downlink=d_rx)


def build_pulse_usage_share(
    rows: Iterable[tuple[int, str, int]],
    *,
    start: dt | None = None,
    end: dt | None = None,
) -> PulseUsageShareResponse:
    """
    Rank pulses by total traffic share.

    rows: (pulse_id, name, bytes)
    """
    merged: dict[int, tuple[str, int]] = {}
    for pulse_id, name, used in rows:
        amount = int(used or 0)
        if amount <= 0:
            continue
        key = int(pulse_id)
        prev = merged.get(key)
        if prev:
            merged[key] = (prev[0] or name, prev[1] + amount)
        else:
            merged[key] = (name, amount)

    total = sum(amount for _, amount in merged.values())
    items: list[PulseUsageShareItem] = []
    for pulse_id, (name, amount) in merged.items():
        items.append(
            PulseUsageShareItem(
                pulse_id=pulse_id,
                name=name,
                bytes=amount,
                percent=round(amount / total * 100, 1) if total else 0.0,
            )
        )
    items.sort(key=lambda item: (-item.bytes, item.name))
    return PulseUsageShareResponse(total_bytes=total, items=items, start=start, end=end)


def default_usage_window(
    *,
    start: dt | None,
    end: dt | None,
    now: dt | None = None,
) -> tuple[dt, dt]:
    """Default the usage share window to the last 7 days when start/end omitted."""
    now = now or dt.now(UTC)
    resolved_end = end or now
    resolved_start = start or (resolved_end - td(days=7))
    return resolved_start, resolved_end
