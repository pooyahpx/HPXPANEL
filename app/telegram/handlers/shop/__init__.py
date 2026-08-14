from aiogram import F, Router, types
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crud.shop import (
    create_shop_order,
    get_enabled_shop_config,
    get_shop_plan,
    get_telegram_lang,
    has_test_claimed,
    list_active_plans,
    list_buyer_orders,
    mark_test_claimed,
    set_telegram_lang,
)
from app.db.models import ShopOrderStatus, UserStatus
from app.models.admin import AdminDetails
from app.models.user import UserCreate
from app.operation import OperatorType
from app.operation.user import UserOperation
from app.telegram.keyboards.shop import (
    LangKeyboard,
    ShopAction,
    ShopHomeKeyboard,
    ShopKeyboard,
    ShopOrderAdminKeyboard,
    ShopPlansKeyboard,
)
from app.telegram.utils import forms
from app.telegram.utils.i18n import format_bytes, format_price, rich, t
from app.telegram.utils.shared import add_to_messages_to_delete
from app.telegram.utils.shop_helpers import (
    build_pay_card_section,
    buyer_show_test_button,
    notify_admins_user_joined,
    notify_shop_admin_support,
    send_card_photos,
    shop_home_text,
)

user_operator = UserOperation(OperatorType.TELEGRAM)

router = Router(name="shop")


async def _lang(db: AsyncSession, telegram_id: int) -> str:
    return (await get_telegram_lang(db, telegram_id)) or "fa"


def _shop_home_text(lang: str, config) -> str:
    return shop_home_text(lang, config)


async def _home_markup(db: AsyncSession, lang: str, telegram_id: int, config):
    show_test = await buyer_show_test_button(db, telegram_id, config)
    return ShopHomeKeyboard(lang, show_test=show_test).as_markup()


async def render_shop_home(message: types.Message, db: AsyncSession, lang: str):
    config = await get_enabled_shop_config(db)
    if not config or not config.enabled:
        await message.answer(t(lang, "shop_disabled"), reply_markup=ShopHomeKeyboard(lang).as_markup())
        return
    markup = await _home_markup(db, lang, message.chat.id, config)
    await message.answer(_shop_home_text(lang, config), reply_markup=markup)


@router.callback_query(LangKeyboard.Callback.filter())
async def set_language(
    event: types.CallbackQuery,
    callback_data: LangKeyboard.Callback,
    db: AsyncSession,
    admin: AdminDetails | None,
    state: FSMContext,
):
    lang = callback_data.code if callback_data.code in ("fa", "en") else "fa"
    await set_telegram_lang(db, event.from_user.id, lang)
    await event.answer(t(lang, "lang_set"))
    try:
        await event.message.delete()
    except TelegramBadRequest:
        pass
    from app.db.crud.admin import build_admin_details, claim_owner_telegram_id
    from app.telegram.handlers.base import open_main_menu

    if admin is None:
        claimed = await claim_owner_telegram_id(db, event.from_user.id, force=False)
        if claimed is not None:
            admin = build_admin_details(claimed, include_loaded_metrics=True)
            await event.message.answer(t(lang, "owner_claimed"))

    if admin is None and event.from_user:
        from app.telegram import get_bot

        bot = get_bot()
        await notify_admins_user_joined(db, bot, event.from_user)

    await open_main_menu(event.message, db, admin, lang)


@router.callback_query(ShopKeyboard.Callback.filter(ShopAction.lang == F.action))
async def change_language(event: types.CallbackQuery, db: AsyncSession):
    lang = await _lang(db, event.from_user.id)
    await event.message.edit_text(t(lang, "choose_lang"), reply_markup=LangKeyboard().as_markup())
    await event.answer()


@router.callback_query(ShopKeyboard.Callback.filter(ShopAction.plans == F.action))
async def shop_plans(event: types.CallbackQuery, db: AsyncSession):
    lang = await _lang(db, event.from_user.id)
    config = await get_enabled_shop_config(db)
    if not config or not config.enabled:
        await event.message.edit_text(t(lang, "shop_disabled"), reply_markup=ShopHomeKeyboard(lang).as_markup())
        await event.answer()
        return
    plans = await list_active_plans(db, config.admin_id)
    text = rich(lang, "shop_plans_prompt")
    if not plans:
        text += f"\n\n{t(lang, 'shop_empty')}"
    await event.message.edit_text(text, reply_markup=ShopPlansKeyboard(lang, plans).as_markup())
    await event.answer()


@router.callback_query(ShopKeyboard.Callback.filter(ShopAction.home == F.action))
async def shop_home(event: types.CallbackQuery, db: AsyncSession):
    lang = await _lang(db, event.from_user.id)
    config = await get_enabled_shop_config(db)
    if not config or not config.enabled:
        await event.message.edit_text(t(lang, "shop_disabled"), reply_markup=ShopHomeKeyboard(lang).as_markup())
        await event.answer()
        return
    markup = await _home_markup(db, lang, event.from_user.id, config)
    await event.message.edit_text(_shop_home_text(lang, config), reply_markup=markup)
    await event.answer()


@router.callback_query(ShopKeyboard.Callback.filter(ShopAction.test == F.action))
async def claim_test_config(event: types.CallbackQuery, db: AsyncSession, admin: AdminDetails | None):
    lang = await _lang(db, event.from_user.id)
    if admin is not None:
        await event.answer("!", show_alert=True)
        return
    config = await get_enabled_shop_config(db)
    if not config or not config.enabled or not config.test_enabled or not config.test_group_ids:
        await event.answer(t(lang, "test_disabled"), show_alert=True)
        return
    if await has_test_claimed(db, event.from_user.id):
        await event.answer(t(lang, "test_already_claimed"), show_alert=True)
        return

    from app.db.crud.admin import build_admin_details, get_admin_by_id
    from datetime import UTC, datetime as dt, timedelta as td
    import secrets

    db_admin = await get_admin_by_id(db, config.admin_id, load_users=False, load_usage_logs=False)
    if not db_admin:
        await event.answer(t(lang, "test_disabled"), show_alert=True)
        return
    admin_details = build_admin_details(db_admin, include_loaded_metrics=True)

    username = f"test{event.from_user.id}_{secrets.token_hex(2)}"
    expire = None
    if config.test_expire_days and config.test_expire_days > 0:
        expire = dt.now(UTC) + td(days=config.test_expire_days)

    new_user = UserCreate(
        username=username,
        status=UserStatus.active,
        data_limit=config.test_data_limit or None,
        expire=expire,
        group_ids=list(config.test_group_ids or []),
        note="shop test config",
    )
    try:
        user = await user_operator.create_user(db, new_user, admin_details)
    except Exception as exc:
        await event.answer(str(exc)[:180], show_alert=True)
        return

    await mark_test_claimed(db, event.from_user.id)
    markup = await _home_markup(db, lang, event.from_user.id, config)
    text = rich(
        lang,
        "test_claim_ok",
        username=user.username,
        url=user.subscription_url,
    )
    await event.message.edit_text(text, reply_markup=markup)
    await event.answer()

    from app.telegram import get_bot

    bot = get_bot()
    if bot:
        try:
            from app.telegram.utils.qr import subscription_qr_file

            await bot.send_photo(event.from_user.id, subscription_qr_file(user.subscription_url, user.username))
        except Exception:
            pass


@router.callback_query(ShopKeyboard.Callback.filter(ShopAction.my_orders == F.action))
async def my_orders(event: types.CallbackQuery, db: AsyncSession):
    lang = await _lang(db, event.from_user.id)
    orders = await list_buyer_orders(db, event.from_user.id)
    if not orders:
        text = t(lang, "my_orders") + "\n\n—"
    else:
        lines = [t(lang, "my_orders"), ""]
        for order in orders:
            plan = await get_shop_plan(db, order.plan_id)
            status_key = {
                ShopOrderStatus.pending: "status_pending",
                ShopOrderStatus.approved: "status_approved",
                ShopOrderStatus.rejected: "status_rejected",
            }[order.status]
            lines.append(
                t(
                    lang,
                    "order_row",
                    id=order.id,
                    plan=plan.name if plan else "?",
                    status=t(lang, status_key),
                    price=format_price(plan.price_toman if plan else 0),
                )
            )
        text = "\n".join(lines)
    config = await get_enabled_shop_config(db)
    await event.message.edit_text(text, reply_markup=await _home_markup(db, lang, event.from_user.id, config))
    await event.answer()


@router.callback_query(ShopKeyboard.Callback.filter(ShopAction.buy == F.action))
async def buy_plan(event: types.CallbackQuery, callback_data: ShopKeyboard.Callback, db: AsyncSession, state: FSMContext):
    lang = await _lang(db, event.from_user.id)
    config = await get_enabled_shop_config(db)
    plan = await get_shop_plan(db, callback_data.plan_id)
    if not config or not config.enabled or not plan or not plan.is_active:
        await event.answer(t(lang, "shop_disabled"), show_alert=True)
        return

    days = t(lang, "days_unlimited") if not plan.expire_days else str(plan.expire_days)
    text = rich(
        lang,
        "pay_title",
        name=plan.name,
        data=format_bytes(plan.data_limit),
        days=days,
        price=format_price(plan.price_toman),
    )
    text += build_pay_card_section(lang, config)

    await state.set_state(forms.ShopBuy.waiting_receipt)
    await state.update_data(plan_id=plan.id, admin_id=config.admin_id, lang=lang)
    await event.message.edit_text(text)

    from app.telegram import get_bot

    bot = get_bot()
    if bot:
        await send_card_photos(bot, event.from_user.id, config)

    tip = await event.message.answer(t(lang, "send_receipt"))
    await add_to_messages_to_delete(state, tip)
    await event.answer()


@router.callback_query(ShopKeyboard.Callback.filter(ShopAction.support == F.action))
async def support_start(event: types.CallbackQuery, db: AsyncSession, state: FSMContext):
    lang = await _lang(db, event.from_user.id)
    config = await get_enabled_shop_config(db)
    if not config or not config.enabled:
        await event.answer(t(lang, "shop_disabled"), show_alert=True)
        return
    await state.set_state(forms.ShopSupport.waiting_message)
    await state.update_data(admin_id=config.admin_id, lang=lang)
    await event.message.edit_text(t(lang, "support_prompt"), reply_markup=await _home_markup(db, lang, event.from_user.id, config))
    await event.answer()


@router.message(forms.ShopSupport.waiting_message, F.text | F.photo)
async def support_message(event: types.Message, db: AsyncSession, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang") or await _lang(db, event.from_user.id)
    admin_id = data.get("admin_id")
    if not admin_id:
        await state.clear()
        await event.answer(t(lang, "shop_disabled"))
        return

    from app.db.crud.admin import get_admin_by_id
    from app.telegram import get_bot

    shop_admin = await get_admin_by_id(db, admin_id, load_users=False, load_usage_logs=False)
    bot = get_bot()
    if shop_admin and shop_admin.telegram_id and bot:
        admin_lang = (await get_telegram_lang(db, shop_admin.telegram_id)) or "fa"
        buyer = event.from_user.username or str(event.from_user.id)
        try:
            await notify_shop_admin_support(
                bot=bot,
                admin_telegram_id=shop_admin.telegram_id,
                admin_lang=admin_lang,
                buyer_telegram_id=event.from_user.id,
                buyer_label=buyer,
                message=event,
            )
        except Exception:
            pass

    await state.clear()
    config = await get_enabled_shop_config(db)
    markup = await _home_markup(db, lang, event.from_user.id, config) if config else ShopHomeKeyboard(lang).as_markup()
    await event.answer(t(lang, "support_sent"), reply_markup=markup)


@router.message(forms.ShopSupport.waiting_message)
async def support_invalid(event: types.Message, state: FSMContext, db: AsyncSession):
    data = await state.get_data()
    lang = data.get("lang") or await _lang(db, event.from_user.id)
    await event.answer(t(lang, "support_prompt"))


@router.message(forms.ShopBuy.waiting_receipt, F.photo)
async def receive_receipt(event: types.Message, db: AsyncSession, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang") or await _lang(db, event.from_user.id)
    plan_id = data.get("plan_id")
    admin_id = data.get("admin_id")
    plan = await get_shop_plan(db, plan_id) if plan_id else None
    if not plan or not admin_id:
        await state.clear()
        await event.answer(t(lang, "shop_disabled"))
        return

    file_id = event.photo[-1].file_id
    order = await create_shop_order(
        db,
        plan_id=plan.id,
        admin_id=admin_id,
        buyer_telegram_id=event.from_user.id,
        buyer_username=event.from_user.username,
        receipt_file_id=file_id,
    )
    await state.clear()
    await event.answer(t(lang, "order_created", id=order.id))

    # Notify shop admin if they have telegram_id
    from app.db.crud.admin import get_admin_by_id

    shop_admin = await get_admin_by_id(db, admin_id, load_users=False, load_usage_logs=False)
    if shop_admin and shop_admin.telegram_id:
        admin_lang = (await get_telegram_lang(db, shop_admin.telegram_id)) or "fa"
        buyer = event.from_user.username or str(event.from_user.id)
        caption = t(
            admin_lang,
            "admin_new_order",
            id=order.id,
            buyer=buyer,
            plan=plan.name,
            price=format_price(plan.price_toman),
        )
        try:
            from app.telegram import get_bot

            bot = get_bot()
            if bot:
                await bot.send_photo(
                    chat_id=shop_admin.telegram_id,
                    photo=file_id,
                    caption=caption,
                    reply_markup=ShopOrderAdminKeyboard(admin_lang, order).as_markup(),
                )
        except Exception:
            pass


@router.message(forms.ShopBuy.waiting_receipt)
async def receipt_not_photo(event: types.Message, state: FSMContext, db: AsyncSession):
    data = await state.get_data()
    lang = data.get("lang") or await _lang(db, event.from_user.id)
    await event.answer(t(lang, "send_receipt"))
