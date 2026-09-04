import asyncio
from collections.abc import Awaitable, Callable


async def confirm_sustained_threshold(
    initial_value: float,
    sampler: Callable[[], Awaitable[float | None]],
    *,
    threshold: float,
    sample_count: int,
    interval: float,
) -> float | None:
    """Return the average only when every sample stays above the threshold."""
    values = [initial_value]
    for _ in range(sample_count - 1):
        if interval:
            await asyncio.sleep(interval)
        try:
            value = await sampler()
        except Exception:
            return None
        if value is None or value < threshold:
            return None
        values.append(value)
    return sum(values) / len(values)
