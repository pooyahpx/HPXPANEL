"""Buyer wallet + referral helpers for Telegram shop."""

from __future__ import annotations

import secrets
import string

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crud.shop import _assign_sqlite_pk, get_or_create_telegram_profile
from app.db.models import (
    ShopBuyerWallet,
    ShopConfig,
    ShopOrder,
    ShopOrderStatus,
    ShopWalletLedger,
    TelegramProfile,
    User,
)


def _make_referral_code(telegram_id: int) -> str:
    alphabet = string.ascii_lowercase + string.digits
    suffix = "".join(secrets.choice(alphabet) for _ in range(4))
    return f"r{telegram_id:x}{suffix}"


async def ensure_referral_code(db: AsyncSession, telegram_id: int) -> str:
    profile = await get_or_create_telegram_profile(db, telegram_id)
    if profile.referral_code:
        return profile.referral_code
    for _ in range(8):
        code = _make_referral_code(telegram_id)
        existing = (
            await db.execute(select(TelegramProfile).where(TelegramProfile.referral_code == code).limit(1))
        ).scalar_one_or_none()
        if existing is None:
            profile.referral_code = code
            await db.commit()
            await db.refresh(profile)
            return code
    raise RuntimeError("Could not allocate referral code")


async def get_profile_by_referral_code(db: AsyncSession, code: str) -> TelegramProfile | None:
    code = (code or "").strip()
    if not code:
        return None
    return (
        await db.execute(select(TelegramProfile).where(TelegramProfile.referral_code == code).limit(1))
    ).scalar_one_or_none()


async def attach_referrer(db: AsyncSession, buyer_telegram_id: int, referrer_telegram_id: int) -> bool:
    """Bind buyer to referrer once. Returns True if newly attached."""
    if buyer_telegram_id == referrer_telegram_id:
        return False
    buyer = await get_or_create_telegram_profile(db, buyer_telegram_id)
    if buyer.referred_by_telegram_id:
        return False
    referrer = await db.get(TelegramProfile, referrer_telegram_id)
    if referrer is None:
        return False
    buyer.referred_by_telegram_id = int(referrer_telegram_id)
    await db.commit()
    return True


async def get_or_create_wallet(db: AsyncSession, admin_id: int, buyer_telegram_id: int) -> ShopBuyerWallet:
    stmt = select(ShopBuyerWallet).where(
        ShopBuyerWallet.admin_id == admin_id,
        ShopBuyerWallet.buyer_telegram_id == buyer_telegram_id,
    )
    wallet = (await db.execute(stmt)).scalar_one_or_none()
    if wallet is not None:
        return wallet
    wallet = ShopBuyerWallet(admin_id=admin_id, buyer_telegram_id=buyer_telegram_id, balance_toman=0)
    await _assign_sqlite_pk(db, ShopBuyerWallet, wallet)
    db.add(wallet)
    await db.commit()
    await db.refresh(wallet)
    return wallet


async def credit_wallet(
    db: AsyncSession,
    *,
    admin_id: int,
    buyer_telegram_id: int,
    amount_toman: int,
    kind: str,
    note: str | None = None,
    order_id: int | None = None,
) -> ShopBuyerWallet:
    if amount_toman == 0:
        return await get_or_create_wallet(db, admin_id, buyer_telegram_id)
    wallet = await get_or_create_wallet(db, admin_id, buyer_telegram_id)
    wallet.balance_toman = int(wallet.balance_toman or 0) + int(amount_toman)
    entry = ShopWalletLedger(
        admin_id=admin_id,
        buyer_telegram_id=buyer_telegram_id,
        amount_toman=int(amount_toman),
        kind=kind,
        note=note,
        order_id=order_id,
    )
    await _assign_sqlite_pk(db, ShopWalletLedger, entry)
    db.add(entry)
    await db.commit()
    await db.refresh(wallet)
    return wallet


async def debit_wallet(
    db: AsyncSession,
    *,
    admin_id: int,
    buyer_telegram_id: int,
    amount_toman: int,
    kind: str = "purchase",
    note: str | None = None,
    order_id: int | None = None,
) -> ShopBuyerWallet:
    amount = abs(int(amount_toman))
    wallet = await get_or_create_wallet(db, admin_id, buyer_telegram_id)
    if int(wallet.balance_toman or 0) < amount:
        raise ValueError("insufficient_wallet_balance")
    return await credit_wallet(
        db,
        admin_id=admin_id,
        buyer_telegram_id=buyer_telegram_id,
        amount_toman=-amount,
        kind=kind,
        note=note,
        order_id=order_id,
    )


async def _latest_shop_user_for_buyer(db: AsyncSession, admin_id: int, buyer_telegram_id: int) -> User | None:
    stmt = (
        select(ShopOrder)
        .where(
            ShopOrder.admin_id == admin_id,
            ShopOrder.buyer_telegram_id == buyer_telegram_id,
            ShopOrder.status == ShopOrderStatus.approved,
            ShopOrder.created_user_id.is_not(None),
        )
        .order_by(ShopOrder.id.desc())
        .limit(1)
    )
    order = (await db.execute(stmt)).scalar_one_or_none()
    if order is None or not order.created_user_id:
        return None
    return await db.get(User, int(order.created_user_id))


async def apply_referral_reward(
    db: AsyncSession,
    *,
    config: ShopConfig,
    buyer_telegram_id: int,
    order_id: int | None = None,
) -> bool:
    """Credit referrer once after invitee's first approved purchase. Returns True if rewarded."""
    if not getattr(config, "referral_enabled", False):
        return False
    profile = await get_or_create_telegram_profile(db, buyer_telegram_id)
    if profile.referral_rewarded or not profile.referred_by_telegram_id:
        return False
    referrer_id = int(profile.referred_by_telegram_id)
    reward_toman = max(0, int(getattr(config, "referral_reward_toman", 0) or 0))
    reward_gb = max(0, int(getattr(config, "referral_reward_data_gb", 0) or 0))
    if reward_toman <= 0 and reward_gb <= 0:
        profile.referral_rewarded = True
        await db.commit()
        return False
    if reward_toman > 0:
        await credit_wallet(
            db,
            admin_id=config.admin_id,
            buyer_telegram_id=referrer_id,
            amount_toman=reward_toman,
            kind="referral",
            note=f"referral reward for order #{order_id}" if order_id else "referral reward",
            order_id=order_id,
        )
    if reward_gb > 0:
        user = await _latest_shop_user_for_buyer(db, config.admin_id, referrer_id)
        if user is not None:
            add_bytes = reward_gb * (1024**3)
            current = int(user.data_limit or 0)
            if current > 0:
                user.data_limit = current + add_bytes
                await db.commit()
    profile = await get_or_create_telegram_profile(db, buyer_telegram_id)
    profile.referral_rewarded = True
    await db.commit()
    return True
