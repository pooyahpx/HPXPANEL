"""Unit tests for HPX Pulse traffic delta + share ranking helpers."""

from datetime import UTC, datetime

from app.services.hpx_pulse.traffic import (
    build_pulse_usage_share,
    compute_counter_delta,
    default_usage_window,
    floor_sample_bucket,
    should_accept_traffic_side,
)


def test_floor_sample_bucket():
    when = datetime(2026, 11, 12, 22, 57, 41, tzinfo=UTC)
    assert floor_sample_bucket(when) == datetime(2026, 11, 12, 22, 50, tzinfo=UTC)


def test_prefer_abroad_over_fresh_iran():
    now = datetime(2026, 11, 12, 12, 0, tzinfo=UTC)
    abroad = datetime(2026, 11, 12, 11, 59, 30, tzinfo=UTC)
    assert should_accept_traffic_side(side="abroad", abroad_last_seen=abroad, now=now) is True
    assert should_accept_traffic_side(side="iran", abroad_last_seen=abroad, now=now) is False
    stale = datetime(2026, 11, 12, 11, 0, tzinfo=UTC)
    assert should_accept_traffic_side(side="iran", abroad_last_seen=stale, now=now) is True


def test_compute_counter_delta_and_reset():
    delta = compute_counter_delta(
        current_rx=150,
        current_tx=90,
        last_rx=100,
        last_tx=40,
        same_side=True,
    )
    assert delta.downlink == 50
    assert delta.uplink == 50

    reset = compute_counter_delta(
        current_rx=10,
        current_tx=5,
        last_rx=100,
        last_tx=40,
        same_side=True,
    )
    assert reset.uplink == 0 and reset.downlink == 0

    baseline = compute_counter_delta(
        current_rx=10,
        current_tx=5,
        last_rx=None,
        last_tx=None,
        same_side=False,
    )
    assert baseline.uplink == 0 and baseline.downlink == 0


def test_build_pulse_usage_share_ranks():
    result = build_pulse_usage_share([(1, "hetz-de", 154), (2, "fin", 82), (3, "empty", 0)])
    assert result.total_bytes == 236
    assert [item.name for item in result.items] == ["hetz-de", "fin"]
    assert result.items[0].percent == 65.3
    assert result.items[1].percent == 34.7


def test_default_usage_window():
    now = datetime(2026, 11, 12, 12, 0, tzinfo=UTC)
    start, end = default_usage_window(start=None, end=None, now=now)
    assert end == now
    assert (end - start).days == 7
