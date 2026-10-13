"""Build the per-node ("config path") traffic share payload."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import datetime as dt

from app.models.subscription import ConfigUsageShareItem, ConfigUsageShareResponse

PANEL_BUCKET_NAME = "Panel"
UNKNOWN_NODE_PREFIX = "Node #"


def build_config_usage_share(
    rows: Iterable[tuple[int | None, int | None]],
    node_names: Mapping[int, str],
    *,
    start: dt | None = None,
    end: dt | None = None,
) -> ConfigUsageShareResponse:
    """
    Turn (node_id, bytes) rows into a ranked share list.

    - node_id None/0 -> the "Panel" bucket
    - node ids that no longer exist -> "Node #<id>"
    - percent = bytes / total * 100, rounded to 1 decimal
    - rows with no traffic are dropped; result sorted by bytes desc
    """
    merged: dict[int, int] = {}
    for node_id, used in rows:
        amount = int(used or 0)
        if amount <= 0:
            continue
        key = int(node_id or 0)
        merged[key] = merged.get(key, 0) + amount

    total = sum(merged.values())
    items: list[ConfigUsageShareItem] = []
    for key, amount in merged.items():
        if key == 0:
            name = PANEL_BUCKET_NAME
        else:
            name = node_names.get(key) or f"{UNKNOWN_NODE_PREFIX}{key}"
        items.append(
            ConfigUsageShareItem(
                node_id=key or None,
                name=name,
                bytes=amount,
                percent=round(amount / total * 100, 1) if total else 0.0,
            )
        )

    items.sort(key=lambda item: (-item.bytes, item.name))
    return ConfigUsageShareResponse(total_bytes=total, items=items, start=start, end=end)
