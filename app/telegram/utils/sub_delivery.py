"""Track telegram-delivered subscriptions and notify buyers when they change."""

from __future__ import annotations

import asyncio
import hashlib
import json
from urllib.parse import urlparse

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select

from app.db.crud.shop import (
    get_owner_admin,
    get_sub_delivery_by_user_id,
    get_telegram_lang,
    update_sub_delivery_version,
    upsert_sub_delivery,
)
from app.db.models import ShopOrder, ShopOrderStatus, User
from app.operation import OperatorType
from app.operation.user import UserOperation
from app.telegram.utils.i18n import rich
from app.utils.logger import get_logger

logger = get_logger("telegram-sub-delivery")
user_operator = UserOperation(OperatorType.SYSTEM)

PAID_SOURCE_TYPES = frozenset({"order", "renewal"})
_domain_notify_lock = asyncio.Lock()


def compute_sub_version(user: User) -> str:
    group_ids = sorted(g.id for g in (user.groups or []))
    payload = {
        "sub_revoked_at": user.sub_revoked_at.isoformat() if user.sub_revoked_at else None,
        "username": user.username,
        "proxy_settings": user.proxy_settings or {},
        "group_ids": group_ids,
        "data_limit": user.data_limit,
        "expire": user.expire.isoformat() if user.expire else None,
    }
    raw = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


async def _load_user(db: AsyncSession, user_id: int) -> User | None:
    stmt = select(User).where(User.id == user_id).options(selectinload(User.groups), selectinload(User.admin))
    return (await db.execute(stmt)).scalar_one_or_none()


async def resolve_user_subscription_url(db: AsyncSession, user_id: int) -> str | None:
    user = await _load_user(db, user_id)
    if user is None:
        return None
    try:
        resp = await user_operator.update_user(user)
        url = (resp.subscription_url or "").strip()
        return url or None
    except Exception as exc:
        logger.warning("Failed to generate subscription url for user %s: %s", user_id, exc)
        return None


async def record_sub_delivery(
    db: AsyncSession,
    *,
    user_id: int,
    buyer_telegram_id: int,
    source_type: str,
    source_id: int | None,
    panel_username: str,
) -> None:
    user = await _load_user(db, user_id)
    if user is None:
        return
    await upsert_sub_delivery(
        db,
        user_id=user_id,
        buyer_telegram_id=buyer_telegram_id,
        source_type=source_type,
        source_id=source_id,
        panel_username=panel_username,
        sub_version=compute_sub_version(user),
    )


async def check_and_notify_sub_change(
    db: AsyncSession,
    user_id: int,
    *,
    reason: str = "change",
    force: bool = False,
) -> bool:
    """If sub fingerprint changed for a tracked telegram buyer, send new URL and notify owner."""
    delivery = await get_sub_delivery_by_user_id(db, user_id)
    if delivery is None:
        return False

    user = await _load_user(db, user_id)
    if user is None:
        return False

    new_version = compute_sub_version(user)
    if not force and new_version == delivery.sub_version:
        return False

    from app.telegram import get_bot

    bot = get_bot()
    if bot is None:
        return False

    user_response = await user_operator.update_user(user)
    sub_url = user_response.subscription_url
    if not sub_url:
        return False

    buyer_lang = (await get_telegram_lang(db, delivery.buyer_telegram_id)) or "fa"
    message_key = "sub_domain_changed_buyer" if reason == "domain" else "sub_updated_buyer"
    text = rich(
        buyer_lang,
        message_key,
        username=user.username,
        url=sub_url,
    )
    sent = False
    try:
        await bot.send_message(delivery.buyer_telegram_id, text, disable_web_page_preview=True)
        sent = True
        try:
            from app.telegram.utils.qr import subscription_qr_file

            await bot.send_photo(
                delivery.buyer_telegram_id,
                subscription_qr_file(sub_url, user.username),
            )
        except Exception:
            pass
    except Exception as exc:
        logger.warning("Failed to send sub update to buyer %s: %s", delivery.buyer_telegram_id, exc)
        return False

    await update_sub_delivery_version(db, delivery, new_version)

    # Domain mass-notify sends one owner summary at the end instead of N spam messages.
    if reason != "domain":
        owner = await get_owner_admin(db)
        if owner and owner.telegram_id:
            owner_lang = (await get_telegram_lang(db, owner.telegram_id)) or "fa"
            source_label = _source_label(owner_lang, delivery)
            reason_label = _reason_label(owner_lang, reason)
            owner_text = rich(
                owner_lang,
                "owner_log_sub_updated",
                username=user.username,
                buyer=str(delivery.buyer_telegram_id),
                source=source_label,
                reason=reason_label,
            )
            try:
                await bot.send_message(owner.telegram_id, owner_text)
            except Exception:
                pass

    logger.info(
        'Telegram sub updated for user "%s" (buyer %s, reason=%s)',
        user.username,
        delivery.buyer_telegram_id,
        reason,
    )
    return sent


def _source_label(lang: str, delivery) -> str:
    from app.telegram.utils.i18n import t

    if delivery.source_type == "test":
        return t(lang, "sub_source_test")
    if delivery.source_id:
        return t(lang, "sub_source_order", id=delivery.source_id)
    return t(lang, "sub_source_order_unknown")


def _reason_label(lang: str, reason: str) -> str:
    from app.telegram.utils.i18n import t

    mapping = {
        "revoke": "sub_reason_revoke",
        "auto": "sub_reason_auto",
        "domain": "sub_reason_domain",
    }
    return t(lang, mapping.get(reason, "sub_reason_change"))


async def resolve_current_sub_origin() -> str:
    """Public subscription URL origin currently used for generated links."""
    from app.utils.helpers import resolve_panel_base_url, resolve_subscription_url_prefix
    from app.settings import subscription_settings

    settings = await subscription_settings()
    panel_base = await resolve_panel_base_url()
    origin = resolve_subscription_url_prefix(settings.url_prefix or "", panel_base)
    return (origin or "").rstrip("/").lower()


def _normalize_origin(value: str | None) -> str:
    raw = (value or "").strip().rstrip("/").lower()
    if not raw:
        return ""
    if "://" not in raw and "." in raw and "/" not in raw:
        raw = f"https://{raw}"
    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}".rstrip("/").lower()
    return raw


async def _read_last_notified_sub_origin(db: AsyncSession) -> str:
    from app.db.crud.settings import get_settings

    db_settings = await get_settings(db)
    raw = db_settings.subscription if isinstance(db_settings.subscription, dict) else {}
    return _normalize_origin(raw.get("last_notified_sub_origin") or "")


async def _write_last_notified_sub_origin(db: AsyncSession, origin: str) -> None:
    from sqlalchemy.orm.attributes import flag_modified

    from app.db.crud.settings import get_settings
    from app.settings import refresh_caches

    db_settings = await get_settings(db)
    sub = dict(db_settings.subscription or {})
    sub["last_notified_sub_origin"] = _normalize_origin(origin)
    db_settings.subscription = sub
    flag_modified(db_settings, "subscription")
    await db.commit()
    await refresh_caches()


async def notify_buyers_subscription_domain_change(*, force: bool = False) -> int:
    """Send the new subscription link to every paid bot buyer when the public domain changes.

    When ``force`` is True (settings save or admin button), always resend.
    Otherwise only send if the resolved origin differs from the last notified one.
    First run with an empty fingerprint seeds the fingerprint and still notifies paid
    buyers once so an already-completed domain migration is covered after upgrade.
    """
    async with _domain_notify_lock:
        from app.db import GetDB
        from app.db.crud.shop import list_sub_deliveries_for_check
        from app.telegram import get_bot

        if get_bot() is None:
            return 0

        current = _normalize_origin(await resolve_current_sub_origin())
        if not current:
            logger.warning("Skipping domain notify: subscription origin is empty")
            return 0

        async with GetDB() as db:
            await backfill_sub_deliveries_from_orders(db)
            last = await _read_last_notified_sub_origin(db)
            if not force and last == current:
                return 0

            notified = 0
            for delivery in await list_sub_deliveries_for_check(db):
                if delivery.source_type not in PAID_SOURCE_TYPES:
                    continue
                if await check_and_notify_sub_change(db, delivery.user_id, reason="domain", force=True):
                    notified += 1
                    await asyncio.sleep(0.05)

            await _write_last_notified_sub_origin(db, current)
            if notified:
                owner = await get_owner_admin(db)
                if owner and owner.telegram_id:
                    owner_lang = (await get_telegram_lang(db, owner.telegram_id)) or "fa"
                    try:
                        await get_bot().send_message(
                            owner.telegram_id,
                            rich(
                                owner_lang,
                                "owner_log_domain_notify",
                                count=notified,
                                origin=current,
                            ),
                        )
                    except Exception:
                        pass
                logger.info(
                    "Domain-change sub notify done: sent=%s origin=%s force=%s",
                    notified,
                    current,
                    force,
                )
            return notified


async def notify_telegram_sub_if_changed(user_id: int, *, reason: str = "change") -> None:
    from app.db import GetDB

    async with GetDB() as db:
        await check_and_notify_sub_change(db, user_id, reason=reason)


async def scan_all_telegram_subs() -> int:
    from app.db import GetDB
    from app.db.crud.shop import list_sub_deliveries_for_check

    domain_notified = await notify_buyers_subscription_domain_change(force=False)

    notified = 0
    async with GetDB() as db:
        await backfill_sub_deliveries_from_orders(db)
        for delivery in await list_sub_deliveries_for_check(db):
            if await check_and_notify_sub_change(db, delivery.user_id, reason="auto"):
                notified += 1
    return domain_notified + notified


async def backfill_sub_deliveries_from_orders(db: AsyncSession) -> int:
    """Create delivery records for approved orders / test users missing one (no notifications)."""
    from app.db.models import ShopOrderStatus

    created = 0
    stmt = (
        select(ShopOrder)
        .where(
            ShopOrder.status == ShopOrderStatus.approved,
            ShopOrder.created_user_id.isnot(None),
        )
        .order_by(ShopOrder.id.asc())
    )
    orders = list((await db.execute(stmt)).scalars().all())
    for order in orders:
        if await get_sub_delivery_by_user_id(db, order.created_user_id):
            continue
        user = await _load_user(db, order.created_user_id)
        if user is None:
            continue
        await upsert_sub_delivery(
            db,
            user_id=user.id,
            buyer_telegram_id=order.buyer_telegram_id,
            source_type="order",
            source_id=order.id,
            panel_username=user.username,
            sub_version=compute_sub_version(user),
        )
        created += 1

    test_stmt = select(User).where(User.note == "shop test config").options(selectinload(User.groups))
    for user in (await db.execute(test_stmt)).scalars().all():
        if await get_sub_delivery_by_user_id(db, user.id):
            continue
        buyer_id = _buyer_id_from_test_username(user.username)
        if buyer_id is None:
            continue
        await upsert_sub_delivery(
            db,
            user_id=user.id,
            buyer_telegram_id=buyer_id,
            source_type="test",
            source_id=None,
            panel_username=user.username,
            sub_version=compute_sub_version(user),
        )
        created += 1
    return created


def _buyer_id_from_test_username(username: str) -> int | None:
    if not username.startswith("t") or "x" not in username[1:]:
        return None
    try:
        return int(username[1 : username.index("x")])
    except (ValueError, IndexError):
        return None
