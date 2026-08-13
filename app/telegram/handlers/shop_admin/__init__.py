import secrets
from datetime import UTC, datetime as dt, timedelta as td

from aiogram import F, Router, types
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crud.admin import build_admin_details, get_admin_by_id
from app.db.crud.shop import (
    create_shop_plan,
    delete_shop_plan,
    get_shop_config_by_admin,
    get_shop_order,
    get_shop_plan,
    get_telegram_lang,
    list_pending_orders,
    list_plans_for_admin,
    set_plan_active,
    update_order_status,
    upsert_shop_config,
)
from app.db.models import ShopOrderStatus, UserStatus
from app.models.admin import AdminDetails
from app.models.user import UserCreate
from app.operation import OperatorType
from app.operation.user import UserOperation
from app.telegram.keyboards.shop import ShopAdminAction, ShopAdminKeyboard, ShopAdminPlansKeyboard
from app.telegram.utils import forms
from app.telegram.utils.filters import IsAdminFilter
from app.telegram.utils.i18n import format_price, rich, t
from app.telegram.utils.shared import add_to_messages_to_delete
from app.telegram.utils.shop_helpers import card_note_preview, card_photos_count, parse_optional_limit

user_operator = UserOperation(OperatorType.TELEGRAM)
router = Router(name="shop_admin")
router.message.filter(IsAdminFilter())
router.callback_query.filter(IsAdminFilter())

GB = 1024**3


async def _lang(db: AsyncSession, telegram_id: int) -> str:
    return (await get_telegram_lang(db, telegram_id)) or "fa"


async def _render_admin_shop(event: types.Message | types.CallbackQuery, db: AsyncSession, admin: AdminDetails):
    lang = await _lang(db, event.from_user.id)
    config = await get_shop_config_by_admin(db, admin.id)
    plans = await list_plans_for_admin(db, admin.id)
    pending = await list_pending_orders(db, admin.id)
    enabled = bool(config and config.enabled)
    text = rich(
        lang,
        "admin_shop_home",
        enabled=t(lang, "yes") if enabled else t(lang, "no"),
        card=config.card_number if config and config.card_number else "—",
        holder=config.card_holder if config and config.card_holder else "—",
        card_note=card_note_preview(config.card_note if config else None, lang),
        card_photos=str(card_photos_count(config)),
        plans=sum(1 for p in plans if p.is_active),
        pending=len(pending),
    )
    markup = ShopAdminKeyboard(lang, enabled).as_markup()
    message = event.message if isinstance(event, types.CallbackQuery) else event
    if isinstance(event, types.CallbackQuery):
        try:
            await message.edit_text(text, reply_markup=markup)
        except TelegramBadRequest:
            await message.answer(text, reply_markup=markup)
        await event.answer()
    else:
        await message.answer(text, reply_markup=markup)


@router.callback_query(ShopAdminKeyboard.Callback.filter(ShopAdminAction.home == F.action))
async def shop_admin_home(event: types.CallbackQuery, callback_data: ShopAdminKeyboard.Callback, db: AsyncSession, admin: AdminDetails):
    if callback_data.id == -1:
        from app.telegram.handlers.base import open_main_menu

        lang = await _lang(db, event.from_user.id)
        await open_main_menu(event.message, db, admin, lang, edit=True)
        await event.answer()
        return
    await _render_admin_shop(event, db, admin)


@router.callback_query(ShopAdminKeyboard.Callback.filter(ShopAdminAction.toggle == F.action))
async def toggle_shop(event: types.CallbackQuery, db: AsyncSession, admin: AdminDetails):
    lang = await _lang(db, event.from_user.id)
    config = await get_shop_config_by_admin(db, admin.id)
    enabled = not bool(config and config.enabled)
    await upsert_shop_config(db, admin.id, enabled=enabled)
    await event.answer(t(lang, "admin_enabled_on" if enabled else "admin_enabled_off"))
    await _render_admin_shop(event, db, admin)


@router.callback_query(ShopAdminKeyboard.Callback.filter(ShopAdminAction.set_card == F.action))
async def ask_card(event: types.CallbackQuery, db: AsyncSession, state: FSMContext):
    lang = await _lang(db, event.from_user.id)
    await state.set_state(forms.ShopAdminCard.card_number)
    await state.update_data(lang=lang)
    msg = await event.message.answer(t(lang, "admin_ask_card"))
    await add_to_messages_to_delete(state, msg)
    await event.answer()


@router.message(forms.ShopAdminCard.card_number)
async def save_card_number(event: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "fa")
    await state.update_data(card_number=event.text.strip())
    await state.set_state(forms.ShopAdminCard.card_holder)
    await event.answer(t(lang, "admin_ask_holder"))


@router.message(forms.ShopAdminCard.card_holder)
async def save_card_holder(event: types.Message, db: AsyncSession, state: FSMContext, admin: AdminDetails):
    data = await state.get_data()
    lang = data.get("lang", "fa")
    await upsert_shop_config(
        db,
        admin.id,
        card_number=data.get("card_number"),
        card_holder=event.text.strip(),
    )
    await state.clear()
    await event.answer(t(lang, "admin_card_saved"))
    await _render_admin_shop(event, db, admin)


@router.callback_query(ShopAdminKeyboard.Callback.filter(ShopAdminAction.set_card_note == F.action))
async def ask_card_note(event: types.CallbackQuery, db: AsyncSession, state: FSMContext):
    lang = await _lang(db, event.from_user.id)
    await state.set_state(forms.ShopAdminCardNote.waiting_text)
    await state.update_data(lang=lang)
    msg = await event.message.answer(t(lang, "admin_ask_card_note"))
    await add_to_messages_to_delete(state, msg)
    await event.answer()


@router.message(forms.ShopAdminCardNote.waiting_text)
async def save_card_note(event: types.Message, db: AsyncSession, state: FSMContext, admin: AdminDetails):
    data = await state.get_data()
    lang = data.get("lang", "fa")
    raw = event.text.strip()
    note = None if raw in ("-", "") else raw[:1000]
    await upsert_shop_config(db, admin.id, card_note="" if note is None else note)
    await state.clear()
    await event.answer(t(lang, "admin_card_note_saved"))
    await _render_admin_shop(event, db, admin)


@router.callback_query(ShopAdminKeyboard.Callback.filter(ShopAdminAction.set_card_photos == F.action))
async def ask_card_photos(event: types.CallbackQuery, db: AsyncSession, state: FSMContext, admin: AdminDetails):
    lang = await _lang(db, event.from_user.id)
    config = await get_shop_config_by_admin(db, admin.id)
    existing = list(config.card_photos or []) if config else []
    await state.set_state(forms.ShopAdminCardPhotos.waiting_photos)
    await state.update_data(lang=lang, card_photos=existing)
    msg = await event.message.answer(t(lang, "admin_ask_card_photos"))
    await add_to_messages_to_delete(state, msg)
    await event.answer()


@router.message(forms.ShopAdminCardPhotos.waiting_photos, F.photo)
async def collect_card_photo(event: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "fa")
    photos = list(data.get("card_photos") or [])
    photos.append(event.photo[-1].file_id)
    await state.update_data(card_photos=photos)
    await event.answer(t(lang, "admin_card_photo_added", count=len(photos)))


@router.message(forms.ShopAdminCardPhotos.waiting_photos, F.text)
async def finish_card_photos(event: types.Message, db: AsyncSession, state: FSMContext, admin: AdminDetails):
    data = await state.get_data()
    lang = data.get("lang", "fa")
    cmd = event.text.strip().lower()
    if cmd == "/clear":
        await upsert_shop_config(db, admin.id, card_photos=[])
        await state.clear()
        await event.answer(t(lang, "admin_card_photos_cleared"))
        await _render_admin_shop(event, db, admin)
        return
    if cmd != "/done":
        await event.answer(t(lang, "admin_ask_card_photos"))
        return
    photos = list(data.get("card_photos") or [])
    await upsert_shop_config(db, admin.id, card_photos=photos)
    await state.clear()
    await event.answer(t(lang, "admin_card_photos_saved", count=len(photos)))
    await _render_admin_shop(event, db, admin)


@router.callback_query(ShopAdminKeyboard.Callback.filter(ShopAdminAction.add_plan == F.action))
async def ask_plan_name(event: types.CallbackQuery, db: AsyncSession, state: FSMContext):
    lang = await _lang(db, event.from_user.id)
    await state.set_state(forms.ShopAdminPlan.name)
    await state.update_data(lang=lang)
    msg = await event.message.answer(t(lang, "admin_ask_plan_name"))
    await add_to_messages_to_delete(state, msg)
    await event.answer()


@router.message(forms.ShopAdminPlan.name)
async def plan_name(event: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "fa")
    await state.update_data(name=event.text.strip()[:64])
    await state.set_state(forms.ShopAdminPlan.gb)
    await event.answer(t(lang, "admin_ask_plan_gb"))


@router.message(forms.ShopAdminPlan.gb)
async def plan_gb(event: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "fa")
    try:
        gb = int(event.text.strip())
        if gb < 0:
            raise ValueError
    except ValueError:
        await event.answer(t(lang, "invalid_number"))
        return
    await state.update_data(data_limit=gb * GB)
    await state.set_state(forms.ShopAdminPlan.days)
    await event.answer(t(lang, "admin_ask_plan_days"))


@router.message(forms.ShopAdminPlan.days)
async def plan_days(event: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "fa")
    try:
        days = int(event.text.strip())
        if days < 0:
            raise ValueError
    except ValueError:
        await event.answer(t(lang, "invalid_number"))
        return
    await state.update_data(expire_days=days)
    await state.set_state(forms.ShopAdminPlan.price)
    await event.answer(t(lang, "admin_ask_plan_price"))


@router.message(forms.ShopAdminPlan.price)
async def plan_price(event: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "fa")
    try:
        price = int(event.text.strip().replace(",", "").replace("٬", ""))
        if price < 0:
            raise ValueError
    except ValueError:
        await event.answer(t(lang, "invalid_number"))
        return
    await state.update_data(price_toman=price)
    await state.set_state(forms.ShopAdminPlan.groups)
    await event.answer(t(lang, "admin_ask_plan_groups"))


@router.message(forms.ShopAdminPlan.groups)
async def plan_groups(event: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "fa")
    raw = event.text.strip()
    group_ids: list[int] = []
    if raw not in ("-", "0", ""):
        try:
            group_ids = [int(x.strip()) for x in raw.split(",") if x.strip()]
        except ValueError:
            await event.answer(t(lang, "invalid_number"))
            return
    await state.update_data(group_ids=group_ids)
    await state.set_state(forms.ShopAdminPlan.ip_limit)
    await event.answer(t(lang, "admin_ask_plan_ip_limit"))


@router.message(forms.ShopAdminPlan.ip_limit)
async def plan_ip_limit(event: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "fa")
    try:
        ip_limit = parse_optional_limit(event.text)
        if ip_limit == 0:
            raise ValueError
    except ValueError:
        await event.answer(t(lang, "invalid_number"))
        return
    await state.update_data(ip_limit=ip_limit)
    await state.set_state(forms.ShopAdminPlan.hwid_limit)
    await event.answer(t(lang, "admin_ask_plan_hwid_limit"))


@router.message(forms.ShopAdminPlan.hwid_limit)
async def plan_hwid_limit(event: types.Message, db: AsyncSession, state: FSMContext, admin: AdminDetails):
    data = await state.get_data()
    lang = data.get("lang", "fa")
    try:
        hwid_limit = parse_optional_limit(event.text)
    except ValueError:
        await event.answer(t(lang, "invalid_number"))
        return
    plan = await create_shop_plan(
        db,
        admin_id=admin.id,
        name=data["name"],
        data_limit=data["data_limit"],
        expire_days=data["expire_days"],
        price_toman=data["price_toman"],
        group_ids=list(data.get("group_ids") or []),
        ip_limit=data.get("ip_limit"),
        hwid_limit=hwid_limit,
    )
    await state.clear()
    await event.answer(t(lang, "admin_plan_created", name=plan.name))
    await _render_admin_shop(event, db, admin)


@router.callback_query(ShopAdminKeyboard.Callback.filter(ShopAdminAction.list_plans == F.action))
async def list_plans(event: types.CallbackQuery, db: AsyncSession, admin: AdminDetails):
    lang = await _lang(db, event.from_user.id)
    plans = await list_plans_for_admin(db, admin.id)
    text = t(lang, "btn_list_plans")
    if not plans:
        text += f"\n\n{t(lang, 'shop_empty')}"
    await event.message.edit_text(text, reply_markup=ShopAdminPlansKeyboard(lang, plans).as_markup())
    await event.answer()


@router.callback_query(ShopAdminKeyboard.Callback.filter(ShopAdminAction.toggle_plan == F.action))
async def toggle_plan(event: types.CallbackQuery, callback_data: ShopAdminKeyboard.Callback, db: AsyncSession, admin: AdminDetails):
    lang = await _lang(db, event.from_user.id)
    plan = await get_shop_plan(db, callback_data.id)
    if not plan or plan.admin_id != admin.id:
        await event.answer("!", show_alert=True)
        return
    await set_plan_active(db, plan, not plan.is_active)
    await event.answer(
        t(lang, "admin_plan_toggled", name=plan.name, state=t(lang, "active" if plan.is_active else "inactive"))
    )
    plans = await list_plans_for_admin(db, admin.id)
    await event.message.edit_reply_markup(reply_markup=ShopAdminPlansKeyboard(lang, plans).as_markup())


@router.callback_query(ShopAdminKeyboard.Callback.filter(ShopAdminAction.delete_plan == F.action))
async def delete_plan(event: types.CallbackQuery, callback_data: ShopAdminKeyboard.Callback, db: AsyncSession, admin: AdminDetails):
    lang = await _lang(db, event.from_user.id)
    plan = await get_shop_plan(db, callback_data.id)
    if not plan or plan.admin_id != admin.id:
        await event.answer("!", show_alert=True)
        return
    await delete_shop_plan(db, plan)
    await event.answer(t(lang, "admin_plan_deleted"))
    plans = await list_plans_for_admin(db, admin.id)
    await event.message.edit_reply_markup(reply_markup=ShopAdminPlansKeyboard(lang, plans).as_markup())


@router.callback_query(ShopAdminKeyboard.Callback.filter(ShopAdminAction.pending == F.action))
async def pending_orders(event: types.CallbackQuery, db: AsyncSession, admin: AdminDetails):
    lang = await _lang(db, event.from_user.id)
    orders = await list_pending_orders(db, admin.id)
    if not orders:
        await event.answer(t(lang, "admin_pending_empty"), show_alert=True)
        return
    await event.answer()
    from app.telegram import get_bot

    bot = get_bot()
    for order in orders:
        plan = await get_shop_plan(db, order.plan_id)
        caption = t(
            lang,
            "admin_new_order",
            id=order.id,
            buyer=order.buyer_username or str(order.buyer_telegram_id),
            plan=plan.name if plan else "?",
            price=format_price(plan.price_toman if plan else 0),
        )
        from app.telegram.keyboards.shop import ShopOrderAdminKeyboard

        if bot and order.receipt_file_id:
            await bot.send_photo(
                chat_id=event.from_user.id,
                photo=order.receipt_file_id,
                caption=caption,
                reply_markup=ShopOrderAdminKeyboard(lang, order).as_markup(),
            )
        else:
            await event.message.answer(caption, reply_markup=ShopOrderAdminKeyboard(lang, order).as_markup())


@router.callback_query(ShopAdminKeyboard.Callback.filter(ShopAdminAction.approve == F.action))
async def approve_order(event: types.CallbackQuery, callback_data: ShopAdminKeyboard.Callback, db: AsyncSession, admin: AdminDetails):
    lang = await _lang(db, event.from_user.id)
    order = await get_shop_order(db, callback_data.id)
    if not order or order.admin_id != admin.id or order.status != ShopOrderStatus.pending:
        await event.answer("!", show_alert=True)
        return
    plan = await get_shop_plan(db, order.plan_id)
    if not plan:
        await event.answer("!", show_alert=True)
        return

    username = f"tg{order.buyer_telegram_id}_{secrets.token_hex(2)}"
    expire = None
    if plan.expire_days and plan.expire_days > 0:
        expire = dt.now(UTC) + td(days=plan.expire_days)

    db_admin = await get_admin_by_id(db, admin.id, load_users=False, load_usage_logs=False)
    admin_details = build_admin_details(db_admin, include_loaded_metrics=True)

    new_user = UserCreate(
        username=username,
        status=UserStatus.active,
        data_limit=plan.data_limit or None,
        expire=expire,
        group_ids=list(plan.group_ids or []),
        ip_limit=plan.ip_limit,
        hwid_limit=plan.hwid_limit,
        note=f"shop order #{order.id}",
    )
    try:
        user = await user_operator.create_user(db, new_user, admin_details)
    except Exception as exc:
        await event.answer(str(exc)[:180], show_alert=True)
        return

    await update_order_status(db, order, ShopOrderStatus.approved, created_user_id=user.id)
    await event.answer(t(lang, "admin_approved", username=user.username))
    try:
        await event.message.edit_caption(caption=(event.message.caption or "") + f"\n\n✅ {user.username}")
    except TelegramBadRequest:
        pass

    buyer_lang = (await get_telegram_lang(db, order.buyer_telegram_id)) or "fa"
    from app.telegram import get_bot

    bot = get_bot()
    if bot:
        text = rich(
            buyer_lang,
            "order_approved",
            id=order.id,
            username=user.username,
            url=user.subscription_url,
        )
        try:
            await bot.send_message(order.buyer_telegram_id, text)
            from app.telegram.utils.qr import subscription_qr_file

            await bot.send_photo(order.buyer_telegram_id, subscription_qr_file(user.subscription_url, user.username))
        except Exception:
            try:
                await bot.send_message(order.buyer_telegram_id, text)
            except Exception:
                pass


@router.callback_query(ShopAdminKeyboard.Callback.filter(ShopAdminAction.reject == F.action))
async def reject_order(event: types.CallbackQuery, callback_data: ShopAdminKeyboard.Callback, db: AsyncSession, admin: AdminDetails):
    lang = await _lang(db, event.from_user.id)
    order = await get_shop_order(db, callback_data.id)
    if not order or order.admin_id != admin.id or order.status != ShopOrderStatus.pending:
        await event.answer("!", show_alert=True)
        return
    await update_order_status(db, order, ShopOrderStatus.rejected)
    await event.answer(t(lang, "admin_rejected"))
    try:
        await event.message.edit_caption(caption=(event.message.caption or "") + "\n\n❌")
    except TelegramBadRequest:
        pass
    from app.telegram import get_bot

    bot = get_bot()
    buyer_lang = (await get_telegram_lang(db, order.buyer_telegram_id)) or "fa"
    if bot:
        try:
            await bot.send_message(order.buyer_telegram_id, t(buyer_lang, "order_rejected", id=order.id))
        except Exception:
            pass


@router.callback_query(ShopAdminKeyboard.Callback.filter(ShopAdminAction.support_reply == F.action))
async def support_reply_start(
    event: types.CallbackQuery,
    callback_data: ShopAdminKeyboard.Callback,
    db: AsyncSession,
    state: FSMContext,
    admin: AdminDetails,
):
    lang = await _lang(db, event.from_user.id)
    await state.set_state(forms.ShopSupportAdmin.waiting_reply)
    await state.update_data(lang=lang, buyer_telegram_id=callback_data.id)
    await event.answer()
    msg = await event.message.answer(t(lang, "support_reply_prompt"))
    await add_to_messages_to_delete(state, msg)


@router.message(forms.ShopSupportAdmin.waiting_reply, F.text | F.photo)
async def support_reply_send(event: types.Message, state: FSMContext, db: AsyncSession, admin: AdminDetails):
    data = await state.get_data()
    lang = data.get("lang", "fa")
    buyer_id = data.get("buyer_telegram_id")
    if not buyer_id:
        await state.clear()
        return

    buyer_lang = (await get_telegram_lang(db, buyer_id)) or "fa"
    from app.telegram import get_bot

    bot = get_bot()
    if not bot:
        await state.clear()
        return

    try:
        if event.photo:
            caption = t(buyer_lang, "support_reply_received", message=event.caption or "")
            await bot.send_photo(buyer_id, event.photo[-1].file_id, caption=caption)
        else:
            await bot.send_message(
                buyer_id,
                t(buyer_lang, "support_reply_received", message=event.text or ""),
            )
    except Exception as exc:
        await event.answer(str(exc)[:180])
        return

    await state.clear()
    await event.answer(t(lang, "support_reply_sent"))
