from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, CopyTextButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crud.shop import get_shop_order, get_shop_plan, list_approved_orders
from app.db.crud.user import get_user_by_id
from app.db.models import ShopOrderStatus
from app.telegram.keyboards.admin import AdminPanel, AdminPanelAction
from app.telegram.utils.filters import IsOwnerFilter
from app.telegram.utils.i18n import rich, t
from app.telegram.utils.sub_delivery import backfill_sub_deliveries_from_orders, resolve_user_subscription_url

router = Router(name="sold_subs")

PAGE_SIZE = 8


async def _lang(db: AsyncSession, telegram_id: int) -> str:
    from app.db.crud.shop import get_telegram_lang

    return (await get_telegram_lang(db, telegram_id)) or "fa"


@router.callback_query(IsOwnerFilter(), AdminPanel.Callback.filter(AdminPanelAction.sold_subs == F.action))
async def sold_subs_list(event: CallbackQuery, callback_data: AdminPanel.Callback, db: AsyncSession):
    lang = await _lang(db, event.from_user.id)
    await backfill_sub_deliveries_from_orders(db)

    page = max(0, callback_data.id)
    offset = page * PAGE_SIZE
    orders, total = await list_approved_orders(db, offset=offset, limit=PAGE_SIZE)

    lines = [rich(lang, "sold_subs_home", total=total), ""]
    kb = InlineKeyboardBuilder()
    cb = AdminPanel.Callback

    if not orders:
        lines.append("—")
    else:
        for order in orders:
            plan = await get_shop_plan(db, order.plan_id)
            plan_name = plan.name if plan else "—"
            username = "—"
            if order.created_user_id:
                db_user = await get_user_by_id(db, order.created_user_id, load_groups=False, load_usage_logs=False)
                if db_user:
                    username = db_user.username
            lines.append(
                rich(
                    lang,
                    "sold_sub_row",
                    order_id=order.id,
                    username=username,
                    buyer=order.buyer_username or order.buyer_telegram_id,
                    plan=plan_name,
                )
            )
            kb.button(
                text=f"🧾 #{order.id} · {username}",
                callback_data=cb(action=AdminPanelAction.sold_sub_detail, id=order.id),
            )

    max_page = max(0, (total - 1) // PAGE_SIZE)
    if page > 0:
        kb.button(text="◀️", callback_data=cb(action=AdminPanelAction.sold_subs, id=page - 1))
    if page < max_page:
        kb.button(text="▶️", callback_data=cb(action=AdminPanelAction.sold_subs, id=page + 1))
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
    order = await get_shop_order(db, callback_data.id)
    if (
        order is None
        or order.status != ShopOrderStatus.approved
        or order.created_user_id is None
    ):
        await event.answer("!", show_alert=True)
        return

    db_user = await get_user_by_id(
        db,
        order.created_user_id,
        load_groups=False,
        load_usage_logs=False,
        load_next_plan=False,
    )
    username = db_user.username if db_user else "—"
    sub_url = await resolve_user_subscription_url(db, order.created_user_id) or "—"

    plan = await get_shop_plan(db, order.plan_id)
    plan_name = plan.name if plan else "—"
    created = order.created_at.strftime("%Y-%m-%d %H:%M") if order.created_at else "—"
    text = rich(
        lang,
        "sold_sub_detail",
        order_id=order.id,
        username=username,
        buyer=str(order.buyer_username or order.buyer_telegram_id),
        plan=plan_name,
        created=created,
        url=sub_url,
    )

    kb = InlineKeyboardBuilder()
    if sub_url != "—":
        kb.button(text=t(lang, "btn_copy_sub"), copy_text=CopyTextButton(text=sub_url))
    kb.button(
        text=t(lang, "btn_back"),
        callback_data=AdminPanel.Callback(action=AdminPanelAction.sold_subs, id=0),
    )
    kb.adjust(1)

    try:
        await event.message.edit_text(text, reply_markup=kb.as_markup(), disable_web_page_preview=True)
    except TelegramBadRequest:
        await event.message.answer(text, reply_markup=kb.as_markup(), disable_web_page_preview=True)
    await event.answer()
