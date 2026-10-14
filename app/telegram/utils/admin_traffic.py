"""Helpers for the owner "edit sub-admin remaining traffic" flow."""

from __future__ import annotations

GB_BYTES = 1024**3
_DIGIT_TRANSLATE = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
_UNLIMITED_WORDS = {"0", "unlimited", "نامحدود", "∞", "none", "-"}


def parse_remaining_input(raw: str) -> int | None:
    """
    Parse owner input into REMAINING bytes.

    ``0`` / ``unlimited`` / ``نامحدود`` → ``None`` (meaning: remove the limit).
    Otherwise a positive number of GB (decimals allowed) → bytes. Raises ValueError on bad input.
    """
    text = (raw or "").strip().lower().translate(_DIGIT_TRANSLATE)
    text = text.replace("٬", "").replace(",", ".").replace("گیگابایت", "").replace("گیگ", "").replace("gb", "").strip()
    if not text:
        raise ValueError("empty")
    if text in _UNLIMITED_WORDS:
        return None
    gb = float(text)
    if gb < 0:
        raise ValueError("negative")
    if gb == 0:
        return None
    return int(gb * GB_BYTES)


def compute_data_limit(used_traffic: int, remaining_bytes: int | None) -> int:
    """
    New ``Admin.data_limit`` from used traffic + desired remaining.

    ``remaining_bytes=None`` → 0, which the panel stores as "unlimited" (0/None = unlimited).
    """
    if remaining_bytes is None:
        return 0
    return max(0, int(used_traffic or 0)) + max(0, int(remaining_bytes))


def remaining_bytes(used_traffic: int, data_limit: int | None) -> int | None:
    """Bytes left (never negative); None when unlimited."""
    if not data_limit:
        return None
    return max(0, int(data_limit) - int(used_traffic or 0))


def format_gb(value: int | None) -> str:
    """Format bytes as GB with 2 decimals; None/0 → ∞."""
    if not value:
        return "∞"
    return f"{value / GB_BYTES:.2f} GB"
