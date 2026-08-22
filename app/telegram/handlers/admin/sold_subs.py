from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crud.shop import get_shop_order, get_shop_plan, get_sub_delivery, list_sub_deliveries
from app.operation import OperatorType
from app.operation.user import UserOperation
from app.telegram.keyboards.admin import AdminPanel, AdminPanelAction
from app.telegram.utils.filters import IsOwnerFilter
from app.telegram.utils.i18n import rich, t
from app.telegram.utils.sub_delivery import _source_label

router = Router(name="sold_subs")
user_operator = UserOperation(OperatorType.SYSTEM)

PAGE_SIZE = 8


async def _lang(db: AsyncSession, telegram_id: int) -> str:
    from app.db.crud.shop import get_telegram_lang

    return (await get_telegram_lang(db, telegram_id)) or "fa"


@router.callback_query(IsOwnerFilter(), AdminPanel.Callback.filter(AdminPanelAction.sold_subs == F.action))
async def sold_subs_list(event: CallbackQuery, callback_data: AdminPanel.Callback, db: AsyncSession):
    lang = await _lang(db, event.from_user.id)
    page = max(0, callback_data.id)
    offset = page * PAGE_SIZE
    deliveries, total = await list_sub_deliveries(db, offset=offset, limit=PAGE_SIZE)

    lines = [rich(lang, "sold_subs_home", total=total), ""]
    kb = InlineKeyboardBuilder()
    cb = AdminPanel.Callback

    if not deliveries:
        lines.append("—")
    else:
        for delivery in deliveries:
            source = _source_label(lang, delivery)
            lines.append(
                t(
                    lang,
                    "sold_sub_row",
                    username=delivery.panel_username,
                    buyer=delivery.buyer_telegram_id,
                    source=source,
                )
            )
            kb.button(
                text=f"🔑 {delivery.panel_username}",
                callback_data=cb(action=AdminPanelAction.sold_sub_detail, id=delivery.id),
            )

    max_page = max(0, (total - 1) // PAGE_SIZE)
    nav_row: list = []
    if page > 0:
        nav_row.append(("◀️", cb(action=AdminPanelAction.sold_subs, id=page - 1)))
    if page < max_page:
        nav_row.append(("▶️", cb(action=AdminPanelAction.sold_subs, id=page + 1)))
    for label, data in nav_row:
        kb.button(text=label, callback_data=data)
    kb.button(text=t(lang, "btn_back"), callback_data=cb(action=AdminPanelAction.refresh))
    kb.adjust(1)

    text = "\n".join(lines)
    markup = kb.as_markup()
    try:
        await event.message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest:
        await event.message.answer(text, reply_markup=markup)
    await event.answer()


@router.callback_query(IsOwnerFilter(), AdminPanel.Callback.filter(AdminPanelAction.sold_sub_detail == F.action))
async def sold_sub_detail(event: CallbackQuery, callback_data: AdminPanel.Callback, db: AsyncSession):
    lang = await _lang(db, event.from_user.id)
    delivery = await get_sub_delivery(db, callback_data.id)
    if delivery is None:
        await event.answer("!", show_alert=True)
        return

    from app.db.crud.user import get_user_by_id

    db_user = await get_user_by_id(db, delivery.user_id, load_groups=True)
    sub_url = "—"
    if db_user:
        user_resp = await user_operator.update_user(db_user)
        sub_url = user_resp.subscription_url or "—"

    plan_name = "—"
    if delivery.source_type == "order" and delivery.source_id:
        order = await get_shop_order(db, delivery.source_id)
        if order:
            plan = await get_shop_plan(db, order.plan_id)
            if plan:
                plan_name = plan.name

    source = _source_label(lang, delivery)
    updated = delivery.updated_at.strftime("%Y-%m-%d %H:%M") if delivery.updated_at else "—"
    text = rich(
        lang,
        "sold_sub_detail",
        username=delivery.panel_username,
        buyer=str(delivery.buyer_telegram_id),
        source=source,
        plan=plan_name,
        updated=updated,
        url=sub_url,
    )

    kb = InlineKeyboardBuilder()
    kb.button(
        text=t(lang, "btn_back"),
        callback_data=AdminPanel.Callback(action=AdminPanelAction.sold_subs, id=0),
    )
    try:
        await event.message.edit_text(text, reply_markup=kb.as_markup(), disable_web_page_preview=True)
    except TelegramBadRequest:
        await event.message.answer(text, reply_markup=kb.as_markup(), disable_web_page_preview=True)
    await event.answer()
