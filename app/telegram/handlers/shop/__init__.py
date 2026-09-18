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
    list_buyer_renewable_accounts,
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
    ShopIpKeyboard,
    ShopKeyboard,
    ShopOrderAdminKeyboard,
    ShopPlansKeyboard,
    ShopRenewAccountsKeyboard,
    ShopRenewPlansKeyboard,
    ShopUsernameKeyboard,
)
from app.telegram.utils import forms
from app.telegram.utils.i18n import format_bytes, format_price, rich, t
from app.telegram.utils.shared import add_to_messages_to_delete
from app.telegram.utils.shop_helpers import (
    build_pay_card_section,
    buyer_show_test_button,
    normalize_group_ids,
    notify_admins_user_joined,
    notify_all_admins_order,
    notify_all_admins_support,
    safe_error_text,
    send_card_photos,
    shop_home_text,
)
from app.models.validators import UserValidator
from app.utils.shop_quote import quote_custom_purchase, validate_custom_bounds

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
    custom_ok = bool(config.custom_enabled) and bool(normalize_group_ids(config.custom_group_ids))
    text = rich(lang, "shop_plans_prompt")
    if not plans and not custom_ok:
        text += f"\n\n{t(lang, 'shop_empty')}"
    await event.message.edit_text(
        text,
        reply_markup=ShopPlansKeyboard(lang, plans, custom_enabled=custom_ok).as_markup(),
    )
    await event.answer()


async def _start_username_choice(event: types.CallbackQuery, state: FSMContext, lang: str, data: dict):
    await state.set_state(forms.ShopBuy.choose_username)
    await state.update_data(**data, lang=lang)
    await event.message.edit_text(
        t(lang, "ask_username_mode"),
        reply_markup=ShopUsernameKeyboard(lang).as_markup(),
    )
    await event.answer()


@router.callback_query(ShopKeyboard.Callback.filter(ShopAction.buy == F.action))
async def buy_plan(event: types.CallbackQuery, callback_data: ShopKeyboard.Callback, db: AsyncSession, state: FSMContext):
    lang = await _lang(db, event.from_user.id)
    config = await get_enabled_shop_config(db)
    plan = await get_shop_plan(db, callback_data.plan_id)
    if not config or not config.enabled or not plan or not plan.is_active:
        await event.answer(t(lang, "shop_disabled"), show_alert=True)
        return
    await _start_username_choice(
        event,
        state,
        lang,
        {
            "plan_id": plan.id,
            "admin_id": config.admin_id,
            "order_kind": "purchase",
            "renew_user_id": None,
            "is_custom": False,
        },
    )


@router.callback_query(ShopKeyboard.Callback.filter(ShopAction.custom == F.action))
async def buy_custom(event: types.CallbackQuery, db: AsyncSession, state: FSMContext):
    lang = await _lang(db, event.from_user.id)
    config = await get_enabled_shop_config(db)
    groups = normalize_group_ids(config.custom_group_ids) if config else []
    if not config or not config.enabled or not config.custom_enabled or not groups:
        await event.answer(t(lang, "custom_not_ready"), show_alert=True)
        return
    await _start_username_choice(
        event,
        state,
        lang,
        {
            "plan_id": None,
            "admin_id": config.admin_id,
            "order_kind": "purchase",
            "renew_user_id": None,
            "is_custom": True,
        },
    )


@router.callback_query(ShopKeyboard.Callback.filter(ShopAction.username_random == F.action))
async def username_random(event: types.CallbackQuery, db: AsyncSession, state: FSMContext):
    lang = await _lang(db, event.from_user.id)
    await state.update_data(requested_username=None, username_label=t(lang, "btn_username_random"))
    await _after_username_chosen(event, db, state, lang)


@router.callback_query(ShopKeyboard.Callback.filter(ShopAction.username_custom == F.action))
async def username_custom_prompt(event: types.CallbackQuery, state: FSMContext, db: AsyncSession):
    lang = await _lang(db, event.from_user.id)
    await state.set_state(forms.ShopBuy.waiting_custom_username)
    await event.message.edit_text(t(lang, "ask_custom_username"))
    await event.answer()


@router.message(forms.ShopBuy.waiting_custom_username)
async def username_custom_value(event: types.Message, db: AsyncSession, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang") or await _lang(db, event.from_user.id)
    raw = (event.text or "").strip()
    try:
        username = UserValidator.validate_username(raw)
    except ValueError:
        await event.answer(t(lang, "invalid_username"))
        return
    await state.update_data(requested_username=username, username_label=username)
    # Fake callback-like path via message
    await _continue_after_username_message(event, db, state, lang)


async def _after_username_chosen(event: types.CallbackQuery, db: AsyncSession, state: FSMContext, lang: str):
    data = await state.get_data()
    if data.get("is_custom"):
        config = await get_enabled_shop_config(db)
        if not config:
            await event.answer(t(lang, "shop_disabled"), show_alert=True)
            return
        await state.set_state(forms.ShopBuy.waiting_gb)
        await event.message.edit_text(
            t(lang, "ask_custom_gb", min=config.custom_min_gb, max=config.custom_max_gb)
        )
        await event.answer()
        return
    await _show_fixed_pay(event, db, state, lang)


async def _continue_after_username_message(event: types.Message, db: AsyncSession, state: FSMContext, lang: str):
    data = await state.get_data()
    if data.get("is_custom"):
        config = await get_enabled_shop_config(db)
        if not config:
            await event.answer(t(lang, "shop_disabled"))
            return
        await state.set_state(forms.ShopBuy.waiting_gb)
        await event.answer(t(lang, "ask_custom_gb", min=config.custom_min_gb, max=config.custom_max_gb))
        return
    await _show_fixed_pay_message(event, db, state, lang)


async def _show_fixed_pay(event: types.CallbackQuery, db: AsyncSession, state: FSMContext, lang: str):
    data = await state.get_data()
    config = await get_enabled_shop_config(db)
    plan = await get_shop_plan(db, data.get("plan_id")) if data.get("plan_id") else None
    if not config or not plan:
        await event.answer(t(lang, "shop_disabled"), show_alert=True)
        return
    days = t(lang, "days_unlimited") if not plan.expire_days else str(plan.expire_days)
    username_label = data.get("username_label") or t(lang, "btn_username_random")
    text = rich(
        lang,
        "pay_title",
        name=plan.name,
        data=format_bytes(plan.data_limit),
        days=days,
        price=format_price(plan.price_toman),
    )
    text += t(lang, "fixed_pay_username", username=username_label)
    text += build_pay_card_section(lang, config)
    await state.set_state(forms.ShopBuy.waiting_receipt)
    await state.update_data(
        quoted_price_toman=int(plan.price_toman or 0),
        custom_data_gb=None,
        custom_expire_days=None,
        custom_ip_limit=plan.ip_limit,
    )
    await event.message.edit_text(text)
    from app.telegram import get_bot

    bot = get_bot()
    if bot:
        await send_card_photos(bot, event.from_user.id, config)
    tip = await event.message.answer(t(lang, "send_receipt"))
    await add_to_messages_to_delete(state, tip)
    await event.answer()


async def _show_fixed_pay_message(event: types.Message, db: AsyncSession, state: FSMContext, lang: str):
    data = await state.get_data()
    config = await get_enabled_shop_config(db)
    plan = await get_shop_plan(db, data.get("plan_id")) if data.get("plan_id") else None
    if not config or not plan:
        await event.answer(t(lang, "shop_disabled"))
        return
    days = t(lang, "days_unlimited") if not plan.expire_days else str(plan.expire_days)
    username_label = data.get("username_label") or t(lang, "btn_username_random")
    text = rich(
        lang,
        "pay_title",
        name=plan.name,
        data=format_bytes(plan.data_limit),
        days=days,
        price=format_price(plan.price_toman),
    )
    text += t(lang, "fixed_pay_username", username=username_label)
    text += build_pay_card_section(lang, config)
    await state.set_state(forms.ShopBuy.waiting_receipt)
    await state.update_data(
        quoted_price_toman=int(plan.price_toman or 0),
        custom_data_gb=None,
        custom_expire_days=None,
        custom_ip_limit=plan.ip_limit,
    )
    await event.answer(text)
    from app.telegram import get_bot

    bot = get_bot()
    if bot:
        await send_card_photos(bot, event.from_user.id, config)
    tip = await event.answer(t(lang, "send_receipt"))
    await add_to_messages_to_delete(state, tip)


@router.message(forms.ShopBuy.waiting_gb)
async def custom_gb(event: types.Message, db: AsyncSession, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang") or await _lang(db, event.from_user.id)
    config = await get_enabled_shop_config(db)
    if not config:
        await event.answer(t(lang, "shop_disabled"))
        return
    try:
        gb = int((event.text or "").strip())
        validate_custom_bounds(
            gb=gb,
            days=config.custom_min_days,
            ip_limit=config.custom_base_ip,
            min_gb=config.custom_min_gb,
            max_gb=config.custom_max_gb,
            min_days=config.custom_min_days,
            max_days=config.custom_max_days,
            base_ip=config.custom_base_ip,
        )
    except (ValueError, TypeError):
        await event.answer(t(lang, "ask_custom_gb", min=config.custom_min_gb, max=config.custom_max_gb))
        return
    await state.update_data(custom_data_gb=gb)
    await state.set_state(forms.ShopBuy.waiting_days)
    await event.answer(t(lang, "ask_custom_days", min=config.custom_min_days, max=config.custom_max_days))


@router.message(forms.ShopBuy.waiting_days)
async def custom_days(event: types.Message, db: AsyncSession, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang") or await _lang(db, event.from_user.id)
    config = await get_enabled_shop_config(db)
    if not config:
        await event.answer(t(lang, "shop_disabled"))
        return
    gb = int(data.get("custom_data_gb") or 0)
    try:
        days = int((event.text or "").strip())
        validate_custom_bounds(
            gb=gb,
            days=days,
            ip_limit=config.custom_base_ip,
            min_gb=config.custom_min_gb,
            max_gb=config.custom_max_gb,
            min_days=config.custom_min_days,
            max_days=config.custom_max_days,
            base_ip=config.custom_base_ip,
        )
    except (ValueError, TypeError):
        await event.answer(t(lang, "ask_custom_days", min=config.custom_min_days, max=config.custom_max_days))
        return
    await state.update_data(custom_expire_days=days)
    await state.set_state(forms.ShopBuy.waiting_ip)
    await event.answer(
        t(lang, "ask_custom_ip", base=config.custom_base_ip),
        reply_markup=ShopIpKeyboard(lang, config.custom_base_ip).as_markup(),
    )


@router.callback_query(ShopKeyboard.Callback.filter(ShopAction.ip_base == F.action))
async def custom_ip_base(event: types.CallbackQuery, db: AsyncSession, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang") or await _lang(db, event.from_user.id)
    config = await get_enabled_shop_config(db)
    if not config:
        await event.answer(t(lang, "shop_disabled"), show_alert=True)
        return
    await state.update_data(custom_ip_limit=int(config.custom_base_ip or 1))
    await _show_custom_pay(event, db, state, lang, config)
    await event.answer()


@router.message(forms.ShopBuy.waiting_ip)
async def custom_ip_value(event: types.Message, db: AsyncSession, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang") or await _lang(db, event.from_user.id)
    config = await get_enabled_shop_config(db)
    if not config:
        await event.answer(t(lang, "shop_disabled"))
        return
    gb = int(data.get("custom_data_gb") or 0)
    days = int(data.get("custom_expire_days") or 0)
    try:
        ip_limit = int((event.text or "").strip())
        validate_custom_bounds(
            gb=gb,
            days=days,
            ip_limit=ip_limit,
            min_gb=config.custom_min_gb,
            max_gb=config.custom_max_gb,
            min_days=config.custom_min_days,
            max_days=config.custom_max_days,
            base_ip=config.custom_base_ip,
        )
    except (ValueError, TypeError):
        await event.answer(
            t(lang, "ask_custom_ip", base=config.custom_base_ip),
            reply_markup=ShopIpKeyboard(lang, config.custom_base_ip).as_markup(),
        )
        return
    await state.update_data(custom_ip_limit=ip_limit)
    # Show pay via message path
    quote = quote_custom_purchase(
        gb=gb,
        days=days,
        ip_limit=ip_limit,
        price_per_gb=config.custom_price_per_gb,
        price_per_day=config.custom_price_per_day,
        price_per_ip=config.custom_price_per_ip,
        base_ip=config.custom_base_ip,
    )
    username_label = data.get("username_label") or t(lang, "btn_username_random")
    text = rich(
        lang,
        "custom_pay_title",
        gb=gb,
        days=days,
        ip=ip_limit,
        username=username_label,
        price=format_price(quote.amount),
    )
    text += build_pay_card_section(lang, config)
    await state.set_state(forms.ShopBuy.waiting_receipt)
    await state.update_data(quoted_price_toman=quote.amount)
    await event.answer(text)
    from app.telegram import get_bot

    bot = get_bot()
    if bot:
        await send_card_photos(bot, event.from_user.id, config)
    tip = await event.answer(t(lang, "send_receipt"))
    await add_to_messages_to_delete(state, tip)


async def _show_custom_pay(event: types.CallbackQuery, db: AsyncSession, state: FSMContext, lang: str, config):
    data = await state.get_data()
    gb = int(data.get("custom_data_gb") or 0)
    days = int(data.get("custom_expire_days") or 0)
    ip_limit = int(data.get("custom_ip_limit") or config.custom_base_ip or 1)
    quote = quote_custom_purchase(
        gb=gb,
        days=days,
        ip_limit=ip_limit,
        price_per_gb=config.custom_price_per_gb,
        price_per_day=config.custom_price_per_day,
        price_per_ip=config.custom_price_per_ip,
        base_ip=config.custom_base_ip,
    )
    username_label = data.get("username_label") or t(lang, "btn_username_random")
    text = rich(
        lang,
        "custom_pay_title",
        gb=gb,
        days=days,
        ip=ip_limit,
        username=username_label,
        price=format_price(quote.amount),
    )
    text += build_pay_card_section(lang, config)
    await state.set_state(forms.ShopBuy.waiting_receipt)
    await state.update_data(quoted_price_toman=quote.amount)
    await event.message.edit_text(text)
    from app.telegram import get_bot

    bot = get_bot()
    if bot:
        await send_card_photos(bot, event.from_user.id, config)
    tip = await event.message.answer(t(lang, "send_receipt"))
    await add_to_messages_to_delete(state, tip)


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
    await event.answer()

    async def _fail(key: str, **kwargs):
        await event.message.answer(t(lang, key, **kwargs))

    if admin is not None:
        await _fail("test_admin_blocked")
        return

    config = await get_enabled_shop_config(db)
    group_ids = normalize_group_ids(config.test_group_ids if config else None)
    if not config or not config.enabled or not config.test_enabled or not group_ids:
        await _fail("test_disabled")
        return
    if await has_test_claimed(db, event.from_user.id):
        await _fail("test_already_claimed")
        return

    from datetime import UTC, datetime as dt, timedelta as td
    import secrets

    from app.db.crud.admin import build_admin_details, get_admin_by_id

    try:
        db_admin = await get_admin_by_id(db, config.admin_id, load_users=False, load_usage_logs=False)
        if not db_admin:
            await _fail("test_disabled")
            return
        admin_details = build_admin_details(db_admin, include_loaded_metrics=False)

        username = f"t{event.from_user.id}x{secrets.token_hex(2)}"
        expire = None
        if config.test_expire_days and config.test_expire_days > 0:
            expire = dt.now(UTC) + td(days=config.test_expire_days)

        data_limit = config.test_data_limit if config.test_data_limit and config.test_data_limit > 0 else None
        new_user = UserCreate(
            username=username,
            status=UserStatus.active,
            data_limit=data_limit,
            expire=expire,
            group_ids=group_ids,
            note="shop test config",
        )
        user = await user_operator.create_user(db, new_user, admin_details, skip_role_limits=True)
    except Exception as exc:
        await _fail("test_create_failed", error=safe_error_text(exc))
        return

    await mark_test_claimed(db, event.from_user.id)
    markup = await _home_markup(db, lang, event.from_user.id, config)
    text = rich(
        lang,
        "test_claim_ok",
        username=user.username,
        url=user.subscription_url,
    )
    try:
        await event.message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest:
        await event.message.answer(text, reply_markup=markup)

    from app.telegram import get_bot

    bot = get_bot()
    if bot:
        try:
            from app.telegram.utils.qr import subscription_qr_file

            await bot.send_photo(event.from_user.id, subscription_qr_file(user.subscription_url, user.username))
        except Exception:
            pass
        from app.telegram.utils.sub_delivery import record_sub_delivery

        await record_sub_delivery(
            db,
            user_id=user.id,
            buyer_telegram_id=event.from_user.id,
            source_type="test",
            source_id=None,
            panel_username=user.username,
        )


@router.callback_query(ShopKeyboard.Callback.filter(ShopAction.my_orders == F.action))
async def my_orders(event: types.CallbackQuery, db: AsyncSession):
    lang = await _lang(db, event.from_user.id)
    orders = await list_buyer_orders(db, event.from_user.id)
    if not orders:
        text = t(lang, "my_orders") + "\n\n—"
    else:
        lines = [t(lang, "my_orders"), ""]
        for order in orders:
            plan = await get_shop_plan(db, order.plan_id) if order.plan_id else None
            status_key = {
                ShopOrderStatus.pending: "status_pending",
                ShopOrderStatus.approved: "status_approved",
                ShopOrderStatus.rejected: "status_rejected",
            }[order.status]
            plan_label = plan.name if plan else ("Custom" if getattr(order, "is_custom", False) else "?")
            price_val = (
                order.quoted_price_toman
                if getattr(order, "quoted_price_toman", None) is not None
                else (plan.price_toman if plan else 0)
            )
            lines.append(
                t(
                    lang,
                    "order_row",
                    id=order.id,
                    plan=plan_label,
                    status=t(lang, status_key),
                    price=format_price(price_val or 0),
                )
            )
        text = "\n".join(lines)
    config = await get_enabled_shop_config(db)
    await event.message.edit_text(text, reply_markup=await _home_markup(db, lang, event.from_user.id, config))
    await event.answer()


@router.callback_query(ShopKeyboard.Callback.filter(ShopAction.renew == F.action))
async def renew_home(event: types.CallbackQuery, db: AsyncSession):
    lang = await _lang(db, event.from_user.id)
    config = await get_enabled_shop_config(db)
    if not config or not config.enabled:
        await event.message.edit_text(t(lang, "shop_disabled"), reply_markup=ShopHomeKeyboard(lang).as_markup())
        await event.answer()
        return
    accounts = await list_buyer_renewable_accounts(
        db, buyer_telegram_id=event.from_user.id, admin_id=config.admin_id
    )
    if not accounts:
        await event.message.edit_text(
            t(lang, "renew_empty"),
            reply_markup=await _home_markup(db, lang, event.from_user.id, config),
        )
        await event.answer()
        return
    await event.message.edit_text(
        rich(lang, "renew_pick_account"),
        reply_markup=ShopRenewAccountsKeyboard(lang, accounts).as_markup(),
    )
    await event.answer()


@router.callback_query(ShopKeyboard.Callback.filter(ShopAction.renew_pick == F.action))
async def renew_pick_account(event: types.CallbackQuery, callback_data: ShopKeyboard.Callback, db: AsyncSession):
    lang = await _lang(db, event.from_user.id)
    config = await get_enabled_shop_config(db)
    if not config or not config.enabled or not callback_data.user_id:
        await event.answer(t(lang, "shop_disabled"), show_alert=True)
        return
    accounts = await list_buyer_renewable_accounts(
        db, buyer_telegram_id=event.from_user.id, admin_id=config.admin_id
    )
    if not any(int(user.id) == int(callback_data.user_id) for user, _ in accounts):
        await event.answer(t(lang, "renew_invalid"), show_alert=True)
        return
    plans = await list_active_plans(db, config.admin_id)
    text = rich(lang, "renew_pick_plan")
    if not plans:
        text += f"\n\n{t(lang, 'shop_empty')}"
    await event.message.edit_text(
        text,
        reply_markup=ShopRenewPlansKeyboard(lang, plans, user_id=int(callback_data.user_id)).as_markup(),
    )
    await event.answer()


@router.callback_query(ShopKeyboard.Callback.filter(ShopAction.renew_buy == F.action))
async def renew_buy_plan(
    event: types.CallbackQuery, callback_data: ShopKeyboard.Callback, db: AsyncSession, state: FSMContext
):
    lang = await _lang(db, event.from_user.id)
    config = await get_enabled_shop_config(db)
    plan = await get_shop_plan(db, callback_data.plan_id)
    if not config or not config.enabled or not plan or not plan.is_active or not callback_data.user_id:
        await event.answer(t(lang, "shop_disabled"), show_alert=True)
        return

    accounts = await list_buyer_renewable_accounts(
        db, buyer_telegram_id=event.from_user.id, admin_id=config.admin_id
    )
    target = next((user for user, _ in accounts if int(user.id) == int(callback_data.user_id)), None)
    if target is None:
        await event.answer(t(lang, "renew_invalid"), show_alert=True)
        return

    days = t(lang, "days_unlimited") if not plan.expire_days else str(plan.expire_days)
    text = rich(
        lang,
        "renew_pay_title",
        username=target.username,
        name=plan.name,
        data=format_bytes(plan.data_limit),
        days=days,
        price=format_price(plan.price_toman),
    )
    text += build_pay_card_section(lang, config)

    await state.set_state(forms.ShopBuy.waiting_receipt)
    await state.update_data(
        plan_id=plan.id,
        admin_id=config.admin_id,
        lang=lang,
        order_kind="renewal",
        renew_user_id=int(target.id),
    )
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

    from app.telegram import get_bot

    bot = get_bot()
    buyer = event.from_user.username or str(event.from_user.id)
    from app.db.crud.shop import open_support_ticket

    await open_support_ticket(db, event.from_user.id)
    if bot:
        try:
            await notify_all_admins_support(
                db,
                bot=bot,
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
    is_custom = bool(data.get("is_custom"))
    plan = await get_shop_plan(db, plan_id) if plan_id else None
    if not admin_id or (not is_custom and not plan):
        await state.clear()
        await event.answer(t(lang, "shop_disabled"))
        return

    file_id = event.photo[-1].file_id
    order_kind = data.get("order_kind") or "purchase"
    renew_user_id = data.get("renew_user_id")
    quoted = data.get("quoted_price_toman")
    if quoted is None and plan is not None:
        quoted = plan.price_toman
    order = await create_shop_order(
        db,
        plan_id=plan.id if plan else None,
        admin_id=admin_id,
        buyer_telegram_id=event.from_user.id,
        buyer_username=event.from_user.username,
        receipt_file_id=file_id,
        order_kind=order_kind,
        renew_user_id=int(renew_user_id) if renew_user_id else None,
        requested_username=data.get("requested_username"),
        custom_data_gb=data.get("custom_data_gb"),
        custom_expire_days=data.get("custom_expire_days"),
        custom_ip_limit=data.get("custom_ip_limit"),
        quoted_price_toman=int(quoted) if quoted is not None else None,
        is_custom=is_custom,
    )
    await state.clear()
    created_key = "renew_order_created" if order_kind == "renewal" else "order_created"
    await event.answer(t(lang, created_key, id=order.id))

    from app.telegram import get_bot

    bot = get_bot()
    if bot:
        buyer = event.from_user.username or str(event.from_user.id)
        plan_name = plan.name if plan else t(lang, "btn_custom_purchase")
        price = format_price(quoted or 0)
        try:
            await notify_all_admins_order(
                db,
                bot=bot,
                buyer_telegram_id=event.from_user.id,
                shop_admin_id=admin_id,
                order_id=order.id,
                buyer_label=buyer,
                plan_name=plan_name,
                price=price,
                file_id=file_id,
                reply_markup_factory=lambda admin_lang: ShopOrderAdminKeyboard(admin_lang, order).as_markup(),
                renewal=order_kind == "renewal",
            )
        except Exception:
            pass


@router.message(forms.ShopBuy.waiting_receipt)
async def receipt_not_photo(event: types.Message, state: FSMContext, db: AsyncSession):
    data = await state.get_data()
    lang = data.get("lang") or await _lang(db, event.from_user.id)
    await event.answer(t(lang, "send_receipt"))
