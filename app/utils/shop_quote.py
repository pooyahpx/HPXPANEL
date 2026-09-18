"""Quote helper for shop custom-volume purchases."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ShopCustomQuote:
    gb: int
    days: int
    ip_limit: int
    base_ip: int
    extra_ip: int
    data_cost: int
    days_cost: int
    ip_cost: int
    amount: int


def quote_custom_purchase(
    *,
    gb: int,
    days: int,
    ip_limit: int,
    price_per_gb: int,
    price_per_day: int,
    price_per_ip: int,
    base_ip: int = 1,
) -> ShopCustomQuote:
    gb = max(0, int(gb))
    days = max(0, int(days))
    ip_limit = max(0, int(ip_limit))
    base_ip = max(0, int(base_ip))
    price_per_gb = max(0, int(price_per_gb))
    price_per_day = max(0, int(price_per_day))
    price_per_ip = max(0, int(price_per_ip))

    extra_ip = max(0, ip_limit - base_ip)
    data_cost = gb * price_per_gb
    days_cost = days * price_per_day
    ip_cost = extra_ip * price_per_ip
    return ShopCustomQuote(
        gb=gb,
        days=days,
        ip_limit=ip_limit,
        base_ip=base_ip,
        extra_ip=extra_ip,
        data_cost=data_cost,
        days_cost=days_cost,
        ip_cost=ip_cost,
        amount=data_cost + days_cost + ip_cost,
    )


def validate_custom_bounds(
    *,
    gb: int,
    days: int,
    ip_limit: int,
    min_gb: int,
    max_gb: int,
    min_days: int,
    max_days: int,
    base_ip: int,
) -> None:
    if gb < min_gb or gb > max_gb:
        raise ValueError(f"GB must be between {min_gb} and {max_gb}")
    if days < min_days or days > max_days:
        raise ValueError(f"Days must be between {min_days} and {max_days}")
    if ip_limit < base_ip:
        raise ValueError(f"IP limit must be at least {base_ip}")
