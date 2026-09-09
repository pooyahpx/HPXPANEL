"""Owner Telegram UI for per-admin create budget (enable, balance, prices)."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crud.admin import get_admin_by_id, get_admins_simple
from app.db.models import Admin
from app.models.admin import AdminDetails, AdminModify, AdminSimpleListQuery, CreateBudgetPriceTier
from app.operation import OperatorType
from app.operation.admin import AdminOperation
from app.telegram.keyboards.admin import AdminPanel, AdminPanelAction
from app.telegram.utils import forms
from app.telegram.utils.filters import IsOwnerFilter
from app.telegram.utils.i18n import rich, t
from app.telegram.utils.shared import add_to_messages_to_delete
from app.utils.admin_create_budget import normalize_price_tiers

admin_operator = AdminOperation(OperatorType.TELEGRAM)

router = Router(name="create_budget")

_BUDGET_FIELDS = {
    "balance": "create_budget_toman",
    "price_gb": "create_budget_price_per_gb",
    "price_day": "create_budget_price_per_day",
}


async def _lang(db: AsyncSession, telegram_id: int) -> str:
    from app.db.crud.shop import get_telegram_lang

    return (await get_telegram_lang(db, telegram_id)) or "fa"


def _fmt_toman(value: int) -> str:
    return f"{int(value or 0):,}"


def _budget_status_line(lang: str, target: Admin) -> str:
    enabled = bool(target.create_budget_enabled)
    status = t(lang, "budget_status_on") if enabled else t(lang, "budget_status_off")
    tiers = normalize_price_tiers(getattr(target, "create_budget_price_tiers", None))
    if tiers:
        tier_lines = []
        for tier in tiers:
            if tier.get("days"):
                tier_lines.append(f"{tier['gb']}GB/{tier['days']}d → {int(tier['price_toman']):,}T")
            else:
                tier_lines.append(f"{tier['gb']}GB → {int(tier['price_toman']):,}T")
        tiers_text = " · ".join(tier_lines)
    else:
        tiers_text = t(lang, "budget_tiers_none")
    return rich(
        lang,
        "budget_admin_detail",
        username=target.username,
        status=status,
        balance=_fmt_toman(target.create_budget_toman),
        price_gb=_fmt_toman(target.create_budget_price_per_gb),
        price_day=_fmt_toman(target.create_budget_price_per_day),
        tiers=tiers_text,
    )


def _budget_admin_kb(lang: str, admin_id: int, enabled: bool):
    kb = InlineKeyboardBuilder()
    cb = AdminPanel.Callback
    toggle_label = t(lang, "budget_btn_disable") if enabled else t(lang, "budget_btn_enable")
    kb.button(text=toggle_label, callback_data=cb(action=AdminPanelAction.budget_toggle, id=admin_id))
    kb.button(
        text=t(lang, "budget_btn_set_balance"),
        callback_data=cb(action=AdminPanelAction.budget_set, id=admin_id, key="balance"),
    )
    kb.button(
        text=t(lang, "budget_btn_set_price_gb"),
        callback_data=cb(action=AdminPanelAction.budget_set, id=admin_id, key="price_gb"),
    )
    kb.button(
        text=t(lang, "budget_btn_set_price_day"),
        callback_data=cb(action=AdminPanelAction.budget_set, id=admin_id, key="price_day"),
    )
    kb.button(
        text=t(lang, "budget_btn_tiers"),
        callback_data=cb(action=AdminPanelAction.budget_tiers, id=admin_id),
    )
    kb.button(
        text=t(lang, "budget_btn_ledger"),
        callback_data=cb(action=AdminPanelAction.budget_ledger, id=admin_id),
    )
    kb.button(text=t(lang, "btn_back"), callback_data=cb(action=AdminPanelAction.manage_create_budget))
    kb.adjust(1, 1, 2, 2, 1)
    return kb.as_markup()


async def _render_budget_home(event: CallbackQuery, db: AsyncSession) -> None:
    lang = await _lang(db, event.from_user.id)
    admin_rows, _ = await get_admins_simple(db, AdminSimpleListQuery(all=True), include_owner=False)

    kb = InlineKeyboardBuilder()
    cb = AdminPanel.Callback
    if not admin_rows:
        text = rich(lang, "budget_home_empty")
    else:
        text = rich(lang, "budget_home")
        for admin_id, username in admin_rows:
            target = await get_admin_by_id(db, admin_id, load_users=False, load_usage_logs=False, load_role=False)
            if target is None:
                continue
            badge = "✅" if target.create_budget_enabled else "⏸"
            label = f"{badge} {username} · {_fmt_toman(target.create_budget_toman)}"
            kb.button(text=label, callback_data=cb(action=AdminPanelAction.budget_admin, id=admin_id))
    kb.button(text=t(lang, "btn_back"), callback_data=cb(action=AdminPanelAction.refresh))
    kb.adjust(1)

    try:
        await event.message.edit_text(text, reply_markup=kb.as_markup())
    except TelegramBadRequest:
        await event.message.answer(text, reply_markup=kb.as_markup())


async def _render_budget_admin(event: CallbackQuery, db: AsyncSession, admin_id: int) -> None:
    lang = await _lang(db, event.from_user.id)
    target = await get_admin_by_id(db, admin_id, load_users=False, load_usage_logs=False, load_role=True)
    if target is None or target.role_id == 1:
        await event.answer(t(lang, "budget_admin_not_found"), show_alert=True)
        return

    text = _budget_status_line(lang, target)
    markup = _budget_admin_kb(lang, target.id, bool(target.create_budget_enabled))
    try:
        await event.message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest:
        await event.message.answer(text, reply_markup=markup)


@router.callback_query(IsOwnerFilter(), AdminPanel.Callback.filter(AdminPanelAction.manage_create_budget == F.action))
async def manage_create_budget_home(event: CallbackQuery, db: AsyncSession, state: FSMContext):
    await state.clear()
    await _render_budget_home(event, db)
    await event.answer()


@router.callback_query(IsOwnerFilter(), AdminPanel.Callback.filter(AdminPanelAction.budget_admin == F.action))
async def budget_admin_detail(event: CallbackQuery, callback_data: AdminPanel.Callback, db: AsyncSession, state: FSMContext):
    await state.clear()
    await _render_budget_admin(event, db, callback_data.id)
    await event.answer()


@router.callback_query(IsOwnerFilter(), AdminPanel.Callback.filter(AdminPanelAction.budget_toggle == F.action))
async def budget_toggle(
    event: CallbackQuery,
    callback_data: AdminPanel.Callback,
    db: AsyncSession,
    admin: AdminDetails,
):
    lang = await _lang(db, event.from_user.id)
    target = await get_admin_by_id(db, callback_data.id, load_users=False, load_usage_logs=False, load_role=True)
    if target is None or target.role_id == 1:
        await event.answer(t(lang, "budget_admin_not_found"), show_alert=True)
        return

    enabled = not bool(target.create_budget_enabled)
    try:
        await admin_operator.modify_admin_by_id(
            db,
            target.id,
            AdminModify(create_budget_enabled=enabled),
            admin,
        )
    except Exception as exc:
        await event.answer(t(lang, "budget_save_fail", error=str(exc)), show_alert=True)
        return

    await event.answer(t(lang, "budget_enabled_on" if enabled else "budget_enabled_off"))
    await _render_budget_admin(event, db, target.id)


@router.callback_query(IsOwnerFilter(), AdminPanel.Callback.filter(AdminPanelAction.budget_set == F.action))
async def budget_set_ask(
    event: CallbackQuery,
    callback_data: AdminPanel.Callback,
    db: AsyncSession,
    state: FSMContext,
):
    lang = await _lang(db, event.from_user.id)
    field_key = callback_data.key or ""
    if field_key not in _BUDGET_FIELDS:
        await event.answer("!", show_alert=True)
        return

    target = await get_admin_by_id(db, callback_data.id, load_users=False, load_usage_logs=False, load_role=True)
    if target is None or target.role_id == 1:
        await event.answer(t(lang, "budget_admin_not_found"), show_alert=True)
        return

    await state.set_state(forms.ManageCreateBudget.waiting_value)
    await state.update_data(lang=lang, budget_admin_id=target.id, budget_field=field_key)
    ask_key = {
        "balance": "budget_ask_balance",
        "price_gb": "budget_ask_price_gb",
        "price_day": "budget_ask_price_day",
    }[field_key]
    msg = await event.message.answer(t(lang, ask_key, username=target.username))
    await add_to_messages_to_delete(state, msg)
    await event.answer()


@router.message(IsOwnerFilter(), forms.ManageCreateBudget.waiting_value)
async def budget_set_value(event: Message, db: AsyncSession, state: FSMContext, admin: AdminDetails):
    data = await state.get_data()
    lang = data.get("lang", "fa")
    admin_id = data.get("budget_admin_id")
    field_key = data.get("budget_field")

    if not admin_id or field_key not in _BUDGET_FIELDS:
        await state.clear()
        await event.answer(t(lang, "budget_save_fail", error="missing data"))
        return

    raw = (event.text or "").strip().replace(",", "").replace("،", "")
    if not raw.isdigit():
        await event.answer(t(lang, "invalid_number"))
        return

    amount = int(raw)
    modify_kwargs = {_BUDGET_FIELDS[field_key]: amount}
    try:
        await admin_operator.modify_admin_by_id(
            db,
            int(admin_id),
            AdminModify(**modify_kwargs),
            admin,
        )
    except Exception as exc:
        await state.clear()
        await event.answer(t(lang, "budget_save_fail", error=str(exc)))
        return

    await state.clear()
    target = await get_admin_by_id(db, int(admin_id), load_users=False, load_usage_logs=False, load_role=True)
    if target is None:
        await event.answer(t(lang, "budget_admin_not_found"))
        return

    text = (
        rich(lang, "budget_saved_ok", username=target.username, amount=_fmt_toman(amount))
        + "\n\n"
        + _budget_status_line(lang, target)
    )
    markup = _budget_admin_kb(lang, target.id, bool(target.create_budget_enabled))
    await event.answer(text, reply_markup=markup)


async def _render_tiers(event: CallbackQuery, db: AsyncSession, admin_id: int) -> None:
    lang = await _lang(db, event.from_user.id)
    target = await get_admin_by_id(db, admin_id, load_users=False, load_usage_logs=False, load_role=True)
    if target is None or target.role_id == 1:
        await event.answer(t(lang, "budget_admin_not_found"), show_alert=True)
        return
    tiers = normalize_price_tiers(getattr(target, "create_budget_price_tiers", None))
    kb = InlineKeyboardBuilder()
    cb = AdminPanel.Callback
    for index, tier in enumerate(tiers):
        if tier.get("days"):
            label = f"🗑 {tier['gb']}GB/{tier['days']}d · {int(tier['price_toman']):,}T"
        else:
            label = f"🗑 {tier['gb']}GB · {int(tier['price_toman']):,}T"
        kb.button(text=label, callback_data=cb(action=AdminPanelAction.budget_tier_del, id=admin_id, key=str(index)))
    kb.button(text=t(lang, "budget_btn_add_tier"), callback_data=cb(action=AdminPanelAction.budget_tier_add, id=admin_id))
    kb.button(text=t(lang, "btn_back"), callback_data=cb(action=AdminPanelAction.budget_admin, id=admin_id))
    kb.adjust(1)
    text = rich(lang, "budget_tiers_home", username=target.username)
    try:
        await event.message.edit_text(text, reply_markup=kb.as_markup())
    except TelegramBadRequest:
        await event.message.answer(text, reply_markup=kb.as_markup())


@router.callback_query(IsOwnerFilter(), AdminPanel.Callback.filter(AdminPanelAction.budget_tiers == F.action))
async def budget_tiers(event: CallbackQuery, callback_data: AdminPanel.Callback, db: AsyncSession, state: FSMContext):
    await state.clear()
    await _render_tiers(event, db, callback_data.id)
    await event.answer()


@router.callback_query(IsOwnerFilter(), AdminPanel.Callback.filter(AdminPanelAction.budget_tier_add == F.action))
async def budget_tier_add_ask(event: CallbackQuery, callback_data: AdminPanel.Callback, db: AsyncSession, state: FSMContext):
    lang = await _lang(db, event.from_user.id)
    await state.set_state(forms.ManageCreateBudget.waiting_tier_gb)
    await state.update_data(lang=lang, budget_admin_id=callback_data.id)
    msg = await event.message.answer(t(lang, "budget_ask_tier_gb"))
    await add_to_messages_to_delete(state, msg)
    await event.answer()


@router.message(IsOwnerFilter(), forms.ManageCreateBudget.waiting_tier_gb)
async def budget_tier_gb(event: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "fa")
    raw = (event.text or "").strip()
    if not raw.isdigit() or int(raw) <= 0:
        await event.answer(t(lang, "invalid_number"))
        return
    await state.update_data(tier_gb=int(raw))
    await state.set_state(forms.ManageCreateBudget.waiting_tier_price)
    msg = await event.answer(t(lang, "budget_ask_tier_price"))
    await add_to_messages_to_delete(state, msg)


@router.message(IsOwnerFilter(), forms.ManageCreateBudget.waiting_tier_price)
async def budget_tier_price(event: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "fa")
    raw = (event.text or "").strip().replace(",", "").replace("،", "")
    if not raw.isdigit():
        await event.answer(t(lang, "invalid_number"))
        return
    await state.update_data(tier_price=int(raw))
    await state.set_state(forms.ManageCreateBudget.waiting_tier_days)
    msg = await event.answer(t(lang, "budget_ask_tier_days"))
    await add_to_messages_to_delete(state, msg)


@router.message(IsOwnerFilter(), forms.ManageCreateBudget.waiting_tier_days)
async def budget_tier_days(event: Message, db: AsyncSession, state: FSMContext, admin: AdminDetails):
    data = await state.get_data()
    lang = data.get("lang", "fa")
    admin_id = data.get("budget_admin_id")
    tier_gb = data.get("tier_gb")
    tier_price = data.get("tier_price")
    raw = (event.text or "").strip()
    days = None
    if raw not in {"-", "0", ""}:
        if not raw.isdigit() or int(raw) <= 0:
            await event.answer(t(lang, "invalid_number"))
            return
        days = int(raw)
    if not admin_id or not tier_gb or tier_price is None:
        await state.clear()
        await event.answer(t(lang, "budget_save_fail", error="missing data"))
        return

    target = await get_admin_by_id(db, int(admin_id), load_users=False, load_usage_logs=False, load_role=True)
    if target is None or target.role_id == 1:
        await state.clear()
        await event.answer(t(lang, "budget_admin_not_found"))
        return

    tiers = normalize_price_tiers(getattr(target, "create_budget_price_tiers", None))
    tiers.append({"gb": int(tier_gb), "price_toman": int(tier_price), "days": days})
    tiers = normalize_price_tiers(tiers)
    try:
        await admin_operator.modify_admin_by_id(
            db,
            target.id,
            AdminModify(create_budget_price_tiers=[CreateBudgetPriceTier(**t) for t in tiers]),
            admin,
        )
    except Exception as exc:
        await state.clear()
        await event.answer(t(lang, "budget_save_fail", error=str(exc)))
        return

    await state.clear()
    await event.answer(t(lang, "budget_tier_saved"))
    # Re-render tiers via a fresh callback-like message
    target = await get_admin_by_id(db, target.id, load_users=False, load_usage_logs=False, load_role=True)
    tiers = normalize_price_tiers(getattr(target, "create_budget_price_tiers", None))
    kb = InlineKeyboardBuilder()
    cb = AdminPanel.Callback
    for index, tier in enumerate(tiers):
        if tier.get("days"):
            label = f"🗑 {tier['gb']}GB/{tier['days']}d · {int(tier['price_toman']):,}T"
        else:
            label = f"🗑 {tier['gb']}GB · {int(tier['price_toman']):,}T"
        kb.button(text=label, callback_data=cb(action=AdminPanelAction.budget_tier_del, id=target.id, key=str(index)))
    kb.button(text=t(lang, "budget_btn_add_tier"), callback_data=cb(action=AdminPanelAction.budget_tier_add, id=target.id))
    kb.button(text=t(lang, "btn_back"), callback_data=cb(action=AdminPanelAction.budget_admin, id=target.id))
    kb.adjust(1)
    await event.answer(rich(lang, "budget_tiers_home", username=target.username), reply_markup=kb.as_markup())


@router.callback_query(IsOwnerFilter(), AdminPanel.Callback.filter(AdminPanelAction.budget_tier_del == F.action))
async def budget_tier_del(
    event: CallbackQuery,
    callback_data: AdminPanel.Callback,
    db: AsyncSession,
    admin: AdminDetails,
):
    lang = await _lang(db, event.from_user.id)
    target = await get_admin_by_id(db, callback_data.id, load_users=False, load_usage_logs=False, load_role=True)
    if target is None or target.role_id == 1:
        await event.answer(t(lang, "budget_admin_not_found"), show_alert=True)
        return
    tiers = normalize_price_tiers(getattr(target, "create_budget_price_tiers", None))
    try:
        index = int(callback_data.key or "-1")
    except ValueError:
        index = -1
    if index < 0 or index >= len(tiers):
        await event.answer("!", show_alert=True)
        return
    tiers.pop(index)
    try:
        await admin_operator.modify_admin_by_id(
            db,
            target.id,
            AdminModify(create_budget_price_tiers=[CreateBudgetPriceTier(**t) for t in tiers]),
            admin,
        )
    except Exception as exc:
        await event.answer(t(lang, "budget_save_fail", error=str(exc)), show_alert=True)
        return
    await event.answer(t(lang, "budget_tier_deleted"))
    await _render_tiers(event, db, target.id)


@router.callback_query(IsOwnerFilter(), AdminPanel.Callback.filter(AdminPanelAction.budget_ledger == F.action))
async def budget_ledger(event: CallbackQuery, callback_data: AdminPanel.Callback, db: AsyncSession):
    from app.db.crud.create_budget_ledger import list_create_budget_ledger

    lang = await _lang(db, event.from_user.id)
    target = await get_admin_by_id(db, callback_data.id, load_users=False, load_usage_logs=False, load_role=True)
    if target is None or target.role_id == 1:
        await event.answer(t(lang, "budget_admin_not_found"), show_alert=True)
        return
    rows, total = await list_create_budget_ledger(db, admin_id=target.id, offset=0, limit=15)
    if not rows:
        body = t(lang, "budget_ledger_empty")
    else:
        lines = []
        for row in rows:
            sign = "+" if row.amount_toman >= 0 else ""
            created = row.created_at.strftime("%m-%d %H:%M") if row.created_at else "—"
            user = row.username or "—"
            lines.append(
                f"• {created} · {row.entry_type} · {sign}{row.amount_toman:,}T · "
                f"{row.billable_gb}GB/{row.billable_days}d · {user} · bal {row.balance_after:,}"
            )
        body = "\n".join(lines)
    text = rich(lang, "budget_ledger_home", username=target.username, total=total, body=body)
    kb = InlineKeyboardBuilder()
    kb.button(
        text=t(lang, "btn_back"),
        callback_data=AdminPanel.Callback(action=AdminPanelAction.budget_admin, id=target.id),
    )
    kb.adjust(1)
    try:
        await event.message.edit_text(text, reply_markup=kb.as_markup())
    except TelegramBadRequest:
        await event.message.answer(text, reply_markup=kb.as_markup())
    await event.answer()
