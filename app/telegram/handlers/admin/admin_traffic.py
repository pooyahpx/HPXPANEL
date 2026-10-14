"""Owner Telegram UI: edit a sub-admin's remaining traffic (and optionally reset used traffic)."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crud.admin import get_admin_by_id, list_admins_with_telegram
from app.models.admin import AdminDetails, AdminModify
from app.operation import OperatorType
from app.operation.admin import AdminOperation
from app.telegram.keyboards.admin import AdminPanel, AdminPanelAction
from app.telegram.utils import forms
from app.telegram.utils.admin_traffic import (
    compute_data_limit,
    format_gb,
    parse_remaining_input,
    remaining_bytes,
)
from app.telegram.utils.filters import IsOwnerFilter
from app.telegram.utils.i18n import rich, t
from app.telegram.utils.shared import add_to_messages_to_delete

admin_operator = AdminOperation(OperatorType.TELEGRAM)

router = Router(name="admin_traffic")


async def _lang(db: AsyncSession, telegram_id: int) -> str:
    from app.db.crud.shop import get_telegram_lang

    return (await get_telegram_lang(db, telegram_id)) or "fa"


def _usage_line(target) -> str:
    used = int(target.used_traffic or 0)
    limit = int(target.data_limit or 0)
    left = remaining_bytes(used, limit)
    return f"{format_gb(used) if used else '0.00 GB'} / {format_gb(limit)} · {format_gb(left)}"


async def _show(event: CallbackQuery, text: str, markup) -> None:
    try:
        await event.message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest:
        await event.message.answer(text, reply_markup=markup)


async def _render_list(event: CallbackQuery, db: AsyncSession) -> None:
    lang = await _lang(db, event.from_user.id)
    admins = [a for a in await list_admins_with_telegram(db) if a.role_id != 1]
    kb = InlineKeyboardBuilder()
    cb = AdminPanel.Callback
    if not admins:
        text = t(lang, "admin_traffic_empty")
    else:
        text = rich(lang, "admin_traffic_home")
        for target in admins:
            label = f"{target.username} · {_usage_line(target)}"
            if len(label) > 60:
                label = label[:57] + "…"
            kb.button(text=label, callback_data=cb(action=AdminPanelAction.admin_traffic_pick, id=target.id))
    kb.button(text=t(lang, "btn_back"), callback_data=cb(action=AdminPanelAction.refresh))
    kb.adjust(1)
    await _show(event, text, kb.as_markup())


async def _render_detail(event: CallbackQuery, db: AsyncSession, admin_id: int) -> None:
    lang = await _lang(db, event.from_user.id)
    target = await get_admin_by_id(db, admin_id, load_users=False, load_usage_logs=False, load_role=True)
    if target is None or target.role_id == 1:
        await event.answer(t(lang, "admin_traffic_not_found"), show_alert=True)
        return
    used = int(target.used_traffic or 0)
    limit = int(target.data_limit or 0)
    text = rich(
        lang,
        "admin_traffic_detail",
        username=target.username,
        used=format_gb(used) if used else "0.00 GB",
        limit=format_gb(limit),
        remaining=format_gb(remaining_bytes(used, limit)),
    )
    kb = InlineKeyboardBuilder()
    cb = AdminPanel.Callback
    kb.button(text=t(lang, "btn_at_set"), callback_data=cb(action=AdminPanelAction.admin_traffic_set, id=target.id))
    kb.button(text=t(lang, "btn_at_reset"), callback_data=cb(action=AdminPanelAction.reset_admin_usage, id=target.id))
    kb.button(text=t(lang, "btn_back"), callback_data=cb(action=AdminPanelAction.admin_traffic))
    kb.adjust(1, 1, 1)
    await _show(event, text, kb.as_markup())


@router.callback_query(IsOwnerFilter(), AdminPanel.Callback.filter(AdminPanelAction.admin_traffic == F.action))
async def admin_traffic_home(event: CallbackQuery, db: AsyncSession, state: FSMContext):
    await state.clear()
    await _render_list(event, db)
    await event.answer()


@router.callback_query(IsOwnerFilter(), AdminPanel.Callback.filter(AdminPanelAction.admin_traffic_pick == F.action))
async def admin_traffic_pick(event: CallbackQuery, callback_data: AdminPanel.Callback, db: AsyncSession, state: FSMContext):
    await state.clear()
    await _render_detail(event, db, callback_data.id)
    await event.answer()


@router.callback_query(IsOwnerFilter(), AdminPanel.Callback.filter(AdminPanelAction.admin_traffic_set == F.action))
async def admin_traffic_set_ask(
    event: CallbackQuery, callback_data: AdminPanel.Callback, db: AsyncSession, state: FSMContext
):
    lang = await _lang(db, event.from_user.id)
    target = await get_admin_by_id(db, callback_data.id, load_users=False, load_usage_logs=False, load_role=True)
    if target is None or target.role_id == 1:
        await event.answer(t(lang, "admin_traffic_not_found"), show_alert=True)
        return
    await state.set_state(forms.AdminTrafficSet.waiting_value)
    await state.update_data(lang=lang, traffic_admin_id=target.id)
    msg = await event.message.answer(t(lang, "admin_traffic_ask", username=target.username))
    await add_to_messages_to_delete(state, msg)
    await event.answer()


@router.message(IsOwnerFilter(), forms.AdminTrafficSet.waiting_value)
async def admin_traffic_set_value(event: Message, db: AsyncSession, state: FSMContext, admin: AdminDetails):
    data = await state.get_data()
    lang = data.get("lang", "fa")
    admin_id = data.get("traffic_admin_id")
    if not admin_id:
        await state.clear()
        await event.answer(t(lang, "admin_traffic_fail", error="missing data"))
        return
    try:
        remaining = parse_remaining_input(event.text or "")
    except ValueError:
        await event.answer(t(lang, "invalid_number"))
        return

    target = await get_admin_by_id(db, int(admin_id), load_users=False, load_usage_logs=False, load_role=True)
    if target is None or target.role_id == 1:
        await state.clear()
        await event.answer(t(lang, "admin_traffic_not_found"))
        return

    new_limit = compute_data_limit(int(target.used_traffic or 0), remaining)
    try:
        await admin_operator.modify_admin_by_id(db, int(admin_id), AdminModify(data_limit=new_limit), admin)
    except Exception as exc:
        await state.clear()
        await event.answer(t(lang, "admin_traffic_fail", error=str(exc)[:200].replace("{", "(").replace("}", ")")))
        return

    await state.clear()
    refreshed = await get_admin_by_id(db, int(admin_id), load_users=False, load_usage_logs=False, load_role=True)
    used = int((refreshed or target).used_traffic or 0)
    limit = int((refreshed or target).data_limit or 0)
    await event.answer(
        t(
            lang,
            "admin_traffic_saved",
            username=target.username,
            used=format_gb(used) if used else "0.00 GB",
            limit=format_gb(limit),
            remaining=format_gb(remaining_bytes(used, limit)),
        )
    )


@router.callback_query(IsOwnerFilter(), AdminPanel.Callback.filter(AdminPanelAction.reset_admin_usage == F.action))
async def admin_traffic_reset(
    event: CallbackQuery, callback_data: AdminPanel.Callback, db: AsyncSession, admin: AdminDetails
):
    lang = await _lang(db, event.from_user.id)
    target = await get_admin_by_id(db, callback_data.id, load_users=False, load_usage_logs=False, load_role=True)
    if target is None or target.role_id == 1:
        await event.answer(t(lang, "admin_traffic_not_found"), show_alert=True)
        return
    try:
        await admin_operator.reset_admin_usage_by_id(db, target.id, admin)
    except Exception as exc:
        await event.answer(t(lang, "admin_traffic_fail", error=str(exc)[:150].replace("{", "(")), show_alert=True)
        return
    await event.answer(t(lang, "admin_traffic_reset_ok", username=target.username), show_alert=True)
    await _render_detail(event, db, target.id)
