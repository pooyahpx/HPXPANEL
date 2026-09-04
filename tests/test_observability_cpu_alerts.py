import pytest

from app.utils import system
from app.utils.observability import confirm_sustained_threshold


@pytest.mark.asyncio
async def test_cpu_alert_rejects_transient_spike() -> None:
    samples = iter([96.0, 25.0])

    async def sampler() -> float:
        return next(samples)

    assert (
        await confirm_sustained_threshold(
            99.0,
            sampler,
            threshold=90.0,
            sample_count=3,
            interval=0,
        )
        is None
    )


@pytest.mark.asyncio
async def test_cpu_alert_accepts_sustained_load() -> None:
    samples = iter([93.0, 96.0])

    async def sampler() -> float:
        return next(samples)

    assert (
        await confirm_sustained_threshold(
            99.0,
            sampler,
            threshold=90.0,
            sample_count=3,
            interval=0,
        )
        == 96.0
    )


def test_cpu_usage_uses_fixed_measurement_window(monkeypatch: pytest.MonkeyPatch) -> None:
    intervals: list[float | None] = []
    monkeypatch.setattr(system.psutil, "cpu_count", lambda: 4)
    monkeypatch.setattr(
        system.psutil,
        "cpu_percent",
        lambda interval=None: intervals.append(interval) or 42.0,
    )

    stats = system.cpu_usage()

    assert stats.percent == 42.0
    assert intervals == [0.25]
