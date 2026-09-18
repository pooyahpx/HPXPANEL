from aiogram import F, Router, types
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crud.shop import (
    create_shop_plan,
    delete_shop_plan,
    get_shop_bot_stats,
    get_shop_config_by_admin,
    get_shop_order,
    get_shop_plan,
    get_telegram_lang,
    list_pending_orders,
    list_plans_for_admin,
    set_plan_active,
    update_order_status,
    update_shop_plan,
    upsert_shop_config,
)
from app.db.models import ShopOrderStatus
from app.models.admin import AdminDetails
from app.operation import OperatorType
from app.telegram.keyboards.shop import (
    PAY_GW_CALLBACK,
    PAY_GW_CARD,
    PAY_GW_IDPAY,
    PAY_GW_NOWPAYMENTS,
    PAY_GW_PAYPAL,
    PAY_GW_STRIPE,
    PAY_GW_ZARINPAL,
    ShopAdminAction,
    ShopAdminCardsKeyboard,
    ShopAdminKeyboard,
    ShopAdminPaymentsKeyboard,
    ShopAdminPlanEditKeyboard,
    ShopAdminPlansKeyboard,
)
from app.telegram.utils import forms
from app.telegram.utils.filters import IsAdminFilter
from app.telegram.utils.i18n import format_bytes, format_price, rich, t
from app.telegram.utils.shared import add_to_messages_to_delete, parse_gb_input
from app.telegram.utils.shop_helpers import (
    MAX_SHOP_CARDS,
    card_note_preview,
    card_photos_count,
    cards_summary,
    custom_config_summary,
    format_groups_hint,
    normalize_group_ids,
    parse_optional_limit,
    shop_cards,
    test_config_summary,
    welcome_note_preview,
)

router = Router(name="shop_admin")
router.message.filter(IsAdminFilter())
router.callback_query.filter(IsAdminFilter())

GB = 1024**3

PLAN_EDIT_FIELDS: dict[ShopAdminAction, tuple[str, str]] = {
    ShopAdminAction.plan_set_name: ("name", "admin_ask_edit_plan_name"),
    ShopAdminAction.plan_set_gb: ("data_limit", "admin_ask_edit_plan_gb"),
    ShopAdminAction.plan_set_days: ("expire_days", "admin_ask_edit_plan_days"),
    ShopAdminAction.plan_set_price: ("price_toman", "admin_ask_edit_plan_price"),
    ShopAdminAction.plan_set_groups: ("group_ids", "admin_ask_edit_plan_groups"),
    ShopAdminAction.plan_set_users: ("ip_limit", "admin_ask_edit_plan_users"),
    ShopAdminAction.plan_set_hwid: ("hwid_limit", "admin_ask_edit_plan_hwid"),
}


def _limit_label(lang: str, value: int | None, *, hwid: bool = False) -> str:
    if value is None:
        return t(lang, "limit_default" if hwid else "limit_unlimited")
    if hwid and value == 0:
        return t(lang, "limit_disabled")
    return str(value)


def _plan_groups_label(plan) -> str:
    groups = plan.group_ids or []
    return ",".join(str(g) for g in groups) if groups else "—"


def _plan_field_current(lang: str, plan, field: str) -> str:
    if field == "name":
        return plan.name
    if field == "data_limit":
        return str(plan.data_limit // GB if plan.data_limit else 0)
    if field == "expire_days":
        return str(plan.expire_days)
    if field == "price_toman":
        return format_price(plan.price_toman)
    if field == "group_ids":
        return _plan_groups_label(plan)
    if field == "ip_limit":
        return _limit_label(lang, plan.ip_limit)
    if field == "hwid_limit":
        return _limit_label(lang, plan.hwid_limit, hwid=True)
    return "—"


def _plan_edit_text(lang: str, plan) -> str:
    days = t(lang, "days_unlimited") if not plan.expire_days else str(plan.expire_days)
    return rich(
        lang,
        "admin_plan_edit",
        name=plan.name,
        data=format_bytes(plan.data_limit),
        days=days,
        price=format_price(plan.price_toman),
        users=_limit_label(lang, plan.ip_limit),
        devices=_limit_label(lang, plan.hwid_limit, hwid=True),
        groups=_plan_groups_label(plan),
    )


async def _render_plan_edit(event: types.Message | types.CallbackQuery, db: AsyncSession, admin: AdminDetails, plan_id: int):
    lang = await _lang(db, event.from_user.id)
    plan = await get_shop_plan(db, plan_id)
    if not plan or plan.admin_id != admin.id:
        return
    text = _plan_edit_text(lang, plan)
    markup = ShopAdminPlanEditKeyboard(lang, plan.id).as_markup()
    message = event.message if isinstance(event, types.CallbackQuery) else event
    if isinstance(event, types.CallbackQuery):
        try:
            await message.edit_text(text, reply_markup=markup)
        except TelegramBadRequest:
            await message.answer(text, reply_markup=markup)
        await event.answer()
    else:
        await message.answer(text, reply_markup=markup)


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
        cards=cards_summary(config, lang),
        card_note=card_note_preview(config.card_note if config else None, lang),
        welcome=welcome_note_preview(config.welcome_note if config else None, lang),
        card_photos=str(card_photos_count(config)),
        test=test_config_summary(config, lang),
        custom=custom_config_summary(config, lang),
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
async def list_cards(event: types.CallbackQuery, db: AsyncSession, admin: AdminDetails):
    await _render_cards_list(event, db, admin)


async def _render_cards_list(event: types.Message | types.CallbackQuery, db: AsyncSession, admin: AdminDetails):
    lang = await _lang(db, event.from_user.id)
    config = await get_shop_config_by_admin(db, admin.id)
    cards = shop_cards(config)
    if cards:
        lines = [rich(lang, "admin_cards_list_title"), ""]
        for index, card in enumerate(cards, start=1):
            lines.append(
                rich(
                    lang,
                    "admin_card_row",
                    index=index,
                    number=card.get("number", "—"),
                    holder=card.get("holder") or "—",
                )
            )
        text = "\n".join(lines)
    else:
        text = t(lang, "admin_cards_empty")
    markup = ShopAdminCardsKeyboard(lang, cards).as_markup()
    message = event.message if isinstance(event, types.CallbackQuery) else event
    if isinstance(event, types.CallbackQuery):
        try:
            await message.edit_text(text, reply_markup=markup)
        except TelegramBadRequest:
            await message.answer(text, reply_markup=markup)
        await event.answer()
    else:
        await message.answer(text, reply_markup=markup)


@router.callback_query(ShopAdminKeyboard.Callback.filter(ShopAdminAction.add_card == F.action))
async def ask_card(event: types.CallbackQuery, db: AsyncSession, state: FSMContext, admin: AdminDetails):
    lang = await _lang(db, event.from_user.id)
    config = await get_shop_config_by_admin(db, admin.id)
    existing = shop_cards(config)
    if len(existing) >= MAX_SHOP_CARDS:
        await event.answer(t(lang, "admin_cards_full"), show_alert=True)
        return
    await state.set_state(forms.ShopAdminCard.card_number)
    await state.update_data(lang=lang, cards=existing, edit_index=None)
    msg = await event.message.answer(t(lang, "admin_ask_card"))
    await add_to_messages_to_delete(state, msg)
    await event.answer()


@router.callback_query(ShopAdminKeyboard.Callback.filter(ShopAdminAction.edit_card == F.action))
async def edit_card_start(
    event: types.CallbackQuery, callback_data: ShopAdminKeyboard.Callback, db: AsyncSession, state: FSMContext, admin: AdminDetails
):
    lang = await _lang(db, event.from_user.id)
    config = await get_shop_config_by_admin(db, admin.id)
    cards = shop_cards(config)
    index = callback_data.id
    if index < 0 or index >= len(cards):
        await event.answer("!", show_alert=True)
        return
    current = cards[index]
    await state.set_state(forms.ShopAdminCard.card_number)
    await state.update_data(lang=lang, cards=cards, edit_index=index)
    msg = await event.message.answer(
        rich(lang, "admin_ask_edit_card", number=current.get("number", "—"), holder=current.get("holder") or "—")
    )
    await add_to_messages_to_delete(state, msg)
    await event.answer()


@router.callback_query(ShopAdminKeyboard.Callback.filter(ShopAdminAction.delete_card == F.action))
async def delete_card(
    event: types.CallbackQuery, callback_data: ShopAdminKeyboard.Callback, db: AsyncSession, admin: AdminDetails
):
    lang = await _lang(db, event.from_user.id)
    config = await get_shop_config_by_admin(db, admin.id)
    cards = shop_cards(config)
    index = callback_data.id
    if index < 0 or index >= len(cards):
        await event.answer("!", show_alert=True)
        return
    removed = cards.pop(index)
    await upsert_shop_config(db, admin.id, cards=cards)
    await event.answer(t(lang, "admin_card_deleted", number=removed.get("number", "")), show_alert=True)
    await _render_cards_list(event, db, admin)


@router.callback_query(ShopAdminKeyboard.Callback.filter(ShopAdminAction.clear_cards == F.action))
async def clear_cards(event: types.CallbackQuery, db: AsyncSession, admin: AdminDetails):
    lang = await _lang(db, event.from_user.id)
    await upsert_shop_config(db, admin.id, cards=[])
    await event.answer(t(lang, "admin_cards_cleared"), show_alert=True)
    await _render_cards_list(event, db, admin)


async def _save_cards(event: types.Message, db: AsyncSession, state: FSMContext, admin: AdminDetails, cards: list[dict[str, str]]):
    data = await state.get_data()
    lang = data.get("lang", "fa")
    await upsert_shop_config(db, admin.id, cards=cards)
    await state.clear()
    await event.answer(t(lang, "admin_card_saved", count=len(cards)))
    await _render_cards_list(event, db, admin)


@router.message(forms.ShopAdminCard.card_number)
async def save_card_number(event: types.Message, db: AsyncSession, state: FSMContext, admin: AdminDetails):
    data = await state.get_data()
    lang = data.get("lang", "fa")
    cmd = event.text.strip().lower()
    cards = list(data.get("cards") or [])
    edit_index = data.get("edit_index")
    if cmd == "/clear":
        await upsert_shop_config(db, admin.id, cards=[])
        await state.clear()
        await event.answer(t(lang, "admin_cards_cleared"))
        await _render_cards_list(event, db, admin)
        return
    if cmd == "/done":
        if edit_index is not None:
            await state.clear()
            await _render_cards_list(event, db, admin)
            return
        if not cards:
            await event.answer(t(lang, "admin_ask_card"))
            return
        await _save_cards(event, db, state, admin, cards)
        return
    await state.update_data(pending_number=event.text.strip())
    await state.set_state(forms.ShopAdminCard.card_holder)
    await event.answer(t(lang, "admin_ask_holder"))


@router.message(forms.ShopAdminCard.card_holder)
async def save_card_holder(event: types.Message, db: AsyncSession, state: FSMContext, admin: AdminDetails):
    data = await state.get_data()
    lang = data.get("lang", "fa")
    cmd = event.text.strip().lower()
    cards = list(data.get("cards") or [])
    edit_index = data.get("edit_index")
    if cmd == "/clear":
        await upsert_shop_config(db, admin.id, cards=[])
        await state.clear()
        await event.answer(t(lang, "admin_cards_cleared"))
        await _render_cards_list(event, db, admin)
        return
    if cmd == "/done":
        if edit_index is not None:
            await state.clear()
            await _render_cards_list(event, db, admin)
            return
        if not cards:
            await event.answer(t(lang, "admin_ask_card"))
            return
        await _save_cards(event, db, state, admin, cards)
        return
    number = data.get("pending_number")
    if not number:
        await state.set_state(forms.ShopAdminCard.card_number)
        await event.answer(t(lang, "admin_ask_card"))
        return
    card = {"number": number, "holder": event.text.strip()}
    if edit_index is not None and 0 <= int(edit_index) < len(cards):
        cards[int(edit_index)] = card
        await _save_cards(event, db, state, admin, cards)
        return
    cards.append(card)
    if len(cards) >= MAX_SHOP_CARDS:
        await _save_cards(event, db, state, admin, cards)
        return
    await state.update_data(cards=cards, pending_number=None, edit_index=None)
    await state.set_state(forms.ShopAdminCard.card_number)
    await event.answer(t(lang, "admin_ask_card_next", count=len(cards), max=MAX_SHOP_CARDS))


@router.callback_query(ShopAdminKeyboard.Callback.filter(ShopAdminAction.stats == F.action))
async def shop_stats(event: types.CallbackQuery, db: AsyncSession, admin: AdminDetails):
    lang = await _lang(db, event.from_user.id)
    stats = await get_shop_bot_stats(db, admin.id)
    text = rich(
        lang,
        "admin_shop_stats",
        buyers=stats["total_buyers"],
        joined=stats["joined"],
        test_claimed=stats["test_claimed"],
        test_accounts=stats["test_accounts"],
        test_used=format_bytes(stats["test_used_bytes"]),
        pending=stats["orders_pending"],
        approved=stats["orders_approved"],
        rejected=stats["orders_rejected"],
    )
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    kb = InlineKeyboardBuilder()
    kb.button(text=t(lang, "btn_back"), callback_data=ShopAdminKeyboard.Callback(action=ShopAdminAction.home))
    kb.adjust(1)
    try:
        await event.message.edit_text(text, reply_markup=kb.as_markup())
    except TelegramBadRequest:
        await event.message.answer(text, reply_markup=kb.as_markup())
    await event.answer()


@router.callback_query(ShopAdminKeyboard.Callback.filter(ShopAdminAction.accounting == F.action))
async def shop_accounting(event: types.CallbackQuery, db: AsyncSession, admin: AdminDetails, callback_data: ShopAdminKeyboard.Callback):
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    from app.db.crud.admin import get_admins_simple
    from app.db.crud.create_budget_ledger import list_create_budget_ledger
    from app.models.admin import AdminSimpleListQuery

    lang = await _lang(db, event.from_user.id)
    kb = InlineKeyboardBuilder()

    # Owner can pick an admin (id>0) or view all (id=0). Non-owner: own ledger only.
    if admin.is_owner and callback_data.id == 0:
        admin_rows, _ = await get_admins_simple(db, AdminSimpleListQuery(all=True), include_owner=False)
        kb.button(
            text=t(lang, "accounting_all"),
            callback_data=ShopAdminKeyboard.Callback(action=ShopAdminAction.accounting, id=-1),
        )
        for admin_id, username in admin_rows:
            kb.button(
                text=f"👤 {username}",
                callback_data=ShopAdminKeyboard.Callback(action=ShopAdminAction.accounting, id=admin_id),
            )
        kb.button(text=t(lang, "btn_back"), callback_data=ShopAdminKeyboard.Callback(action=ShopAdminAction.home))
        kb.adjust(1)
        text = t(lang, "accounting_pick_admin")
        try:
            await event.message.edit_text(text, reply_markup=kb.as_markup())
        except TelegramBadRequest:
            await event.message.answer(text, reply_markup=kb.as_markup())
        await event.answer()
        return

    if admin.is_owner:
        target_id = None if callback_data.id < 0 else callback_data.id
    else:
        target_id = admin.id

    rows, total = await list_create_budget_ledger(db, admin_id=target_id, offset=0, limit=20)
    if not rows:
        body = t(lang, "accounting_empty")
    else:
        lines = []
        for row in rows:
            sign = "+" if row.amount_toman >= 0 else ""
            created = row.created_at.strftime("%m-%d %H:%M") if row.created_at else "—"
            user = row.username or "—"
            lines.append(
                f"• #{row.id} {created} · adm{row.admin_id} · {row.entry_type} · "
                f"{sign}{row.amount_toman:,}T · {row.billable_gb}GB/{row.billable_days}d · {user}"
            )
        body = "\n".join(lines)
    text = rich(lang, "accounting_home", total=total, body=body)
    kb.button(text=t(lang, "btn_back"), callback_data=ShopAdminKeyboard.Callback(action=ShopAdminAction.home))
    if admin.is_owner:
        kb.button(
            text=t(lang, "accounting_pick_admin"),
            callback_data=ShopAdminKeyboard.Callback(action=ShopAdminAction.accounting, id=0),
        )
    kb.adjust(1)
    try:
        await event.message.edit_text(text, reply_markup=kb.as_markup())
    except TelegramBadRequest:
        await event.message.answer(text, reply_markup=kb.as_markup())
    await event.answer()


@router.callback_query(ShopAdminKeyboard.Callback.filter(ShopAdminAction.toggle_test == F.action))
async def toggle_test(event: types.CallbackQuery, db: AsyncSession, admin: AdminDetails):
    lang = await _lang(db, event.from_user.id)
    config = await get_shop_config_by_admin(db, admin.id)
    enabled = not bool(config and config.test_enabled)
    await upsert_shop_config(db, admin.id, test_enabled=enabled)
    await event.answer(t(lang, "admin_test_enabled_on" if enabled else "admin_test_enabled_off"))
    await _render_admin_shop(event, db, admin)


@router.callback_query(ShopAdminKeyboard.Callback.filter(ShopAdminAction.set_test == F.action))
async def ask_test_config(event: types.CallbackQuery, db: AsyncSession, state: FSMContext):
    lang = await _lang(db, event.from_user.id)
    await state.set_state(forms.ShopAdminTest.gb)
    await state.update_data(lang=lang)
    msg = await event.message.answer(t(lang, "admin_ask_test_gb"))
    await add_to_messages_to_delete(state, msg)
    await event.answer()


@router.message(forms.ShopAdminTest.gb)
async def test_gb(event: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "fa")
    try:
        test_data_limit = parse_gb_input(event.text)
    except ValueError:
        await event.answer(t(lang, "invalid_number"))
        return
    await state.update_data(test_data_limit=test_data_limit)
    await state.set_state(forms.ShopAdminTest.days)
    await event.answer(t(lang, "admin_ask_test_days"))


@router.message(forms.ShopAdminTest.days)
async def test_days(event: types.Message, state: FSMContext, db: AsyncSession):
    data = await state.get_data()
    lang = data.get("lang", "fa")
    try:
        days = int(event.text.strip())
        if days < 0:
            raise ValueError
    except ValueError:
        await event.answer(t(lang, "invalid_number"))
        return
    await state.update_data(test_expire_days=days)
    await state.set_state(forms.ShopAdminTest.groups)
    groups = await format_groups_hint(db)
    await event.answer(t(lang, "admin_ask_test_groups", groups=groups))


@router.message(forms.ShopAdminTest.groups)
async def test_groups(event: types.Message, db: AsyncSession, state: FSMContext, admin: AdminDetails):
    data = await state.get_data()
    lang = data.get("lang", "fa")
    raw = event.text.strip()
    group_ids: list[int] = []
    if raw not in ("-", "0", ""):
        group_ids = normalize_group_ids(raw)
        if not group_ids:
            await event.answer(t(lang, "invalid_number"))
            return
    if not group_ids:
        groups = await format_groups_hint(db)
        await event.answer(t(lang, "admin_ask_test_groups", groups=groups))
        return
    await upsert_shop_config(
        db,
        admin.id,
        test_data_limit=data.get("test_data_limit", GB),
        test_expire_days=data.get("test_expire_days", 1),
        test_group_ids=group_ids,
        test_enabled=True,
    )
    await state.clear()
    await event.answer(t(lang, "admin_test_saved"))
    await _render_admin_shop(event, db, admin)


@router.callback_query(ShopAdminKeyboard.Callback.filter(ShopAdminAction.toggle_custom == F.action))
async def toggle_custom(event: types.CallbackQuery, db: AsyncSession, admin: AdminDetails):
    lang = await _lang(db, event.from_user.id)
    config = await get_shop_config_by_admin(db, admin.id)
    currently = bool(config and config.custom_enabled)
    if currently:
        await upsert_shop_config(db, admin.id, custom_enabled=False)
        await event.answer(t(lang, "admin_custom_enabled_off"))
        await _render_admin_shop(event, db, admin)
        return
    groups = list((config.custom_group_ids if config else None) or [])
    if not groups:
        await event.answer(t(lang, "admin_custom_need_setup"), show_alert=True)
        return
    await upsert_shop_config(db, admin.id, custom_enabled=True)
    await event.answer(t(lang, "admin_custom_enabled_on"))
    await _render_admin_shop(event, db, admin)


@router.callback_query(ShopAdminKeyboard.Callback.filter(ShopAdminAction.set_custom == F.action))
async def ask_custom_config(event: types.CallbackQuery, db: AsyncSession, state: FSMContext):
    lang = await _lang(db, event.from_user.id)
    await state.set_state(forms.ShopAdminCustom.price_per_gb)
    await state.update_data(lang=lang)
    msg = await event.message.answer(t(lang, "admin_ask_custom_price_gb"))
    await add_to_messages_to_delete(state, msg)
    await event.answer()


def _parse_nonneg_int(raw: str) -> int:
    value = int(raw.strip().replace(",", "").replace("٬", ""))
    if value < 0:
        raise ValueError
    return value


def _parse_pos_int(raw: str) -> int:
    value = _parse_nonneg_int(raw)
    if value < 1:
        raise ValueError
    return value


@router.message(forms.ShopAdminCustom.price_per_gb)
async def custom_price_gb(event: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "fa")
    try:
        price = _parse_nonneg_int(event.text or "")
    except ValueError:
        await event.answer(t(lang, "invalid_number"))
        return
    await state.update_data(custom_price_per_gb=price)
    await state.set_state(forms.ShopAdminCustom.price_per_day)
    await event.answer(t(lang, "admin_ask_custom_price_day"))


@router.message(forms.ShopAdminCustom.price_per_day)
async def custom_price_day(event: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "fa")
    try:
        price = _parse_nonneg_int(event.text or "")
    except ValueError:
        await event.answer(t(lang, "invalid_number"))
        return
    await state.update_data(custom_price_per_day=price)
    await state.set_state(forms.ShopAdminCustom.price_per_ip)
    await event.answer(t(lang, "admin_ask_custom_price_ip"))


@router.message(forms.ShopAdminCustom.price_per_ip)
async def custom_price_ip(event: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "fa")
    try:
        price = _parse_nonneg_int(event.text or "")
    except ValueError:
        await event.answer(t(lang, "invalid_number"))
        return
    await state.update_data(custom_price_per_ip=price)
    await state.set_state(forms.ShopAdminCustom.min_gb)
    await event.answer(t(lang, "admin_ask_custom_min_gb"))


@router.message(forms.ShopAdminCustom.min_gb)
async def custom_min_gb(event: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "fa")
    try:
        value = _parse_pos_int(event.text or "")
    except ValueError:
        await event.answer(t(lang, "invalid_number"))
        return
    await state.update_data(custom_min_gb=value)
    await state.set_state(forms.ShopAdminCustom.max_gb)
    await event.answer(t(lang, "admin_ask_custom_max_gb"))


@router.message(forms.ShopAdminCustom.max_gb)
async def custom_max_gb(event: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "fa")
    try:
        value = _parse_pos_int(event.text or "")
        if value < int(data.get("custom_min_gb") or 1):
            raise ValueError
    except ValueError:
        await event.answer(t(lang, "invalid_number"))
        return
    await state.update_data(custom_max_gb=value)
    await state.set_state(forms.ShopAdminCustom.min_days)
    await event.answer(t(lang, "admin_ask_custom_min_days"))


@router.message(forms.ShopAdminCustom.min_days)
async def custom_min_days(event: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "fa")
    try:
        value = _parse_pos_int(event.text or "")
    except ValueError:
        await event.answer(t(lang, "invalid_number"))
        return
    await state.update_data(custom_min_days=value)
    await state.set_state(forms.ShopAdminCustom.max_days)
    await event.answer(t(lang, "admin_ask_custom_max_days"))


@router.message(forms.ShopAdminCustom.max_days)
async def custom_max_days(event: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "fa")
    try:
        value = _parse_pos_int(event.text or "")
        if value < int(data.get("custom_min_days") or 1):
            raise ValueError
    except ValueError:
        await event.answer(t(lang, "invalid_number"))
        return
    await state.update_data(custom_max_days=value)
    await state.set_state(forms.ShopAdminCustom.base_ip)
    await event.answer(t(lang, "admin_ask_custom_base_ip"))


@router.message(forms.ShopAdminCustom.base_ip)
async def custom_base_ip(event: types.Message, state: FSMContext, db: AsyncSession):
    data = await state.get_data()
    lang = data.get("lang", "fa")
    try:
        value = _parse_pos_int(event.text or "")
    except ValueError:
        await event.answer(t(lang, "invalid_number"))
        return
    await state.update_data(custom_base_ip=value)
    await state.set_state(forms.ShopAdminCustom.groups)
    groups = await format_groups_hint(db)
    await event.answer(t(lang, "admin_ask_custom_groups", groups=groups))


@router.message(forms.ShopAdminCustom.groups)
async def custom_groups(event: types.Message, db: AsyncSession, state: FSMContext, admin: AdminDetails):
    data = await state.get_data()
    lang = data.get("lang", "fa")
    group_ids = normalize_group_ids(event.text or "")
    if not group_ids:
        groups = await format_groups_hint(db)
        await event.answer(t(lang, "admin_ask_custom_groups", groups=groups))
        return
    await upsert_shop_config(
        db,
        admin.id,
        custom_enabled=True,
        custom_price_per_gb=int(data.get("custom_price_per_gb") or 0),
        custom_price_per_day=int(data.get("custom_price_per_day") or 0),
        custom_price_per_ip=int(data.get("custom_price_per_ip") or 0),
        custom_min_gb=int(data.get("custom_min_gb") or 1),
        custom_max_gb=int(data.get("custom_max_gb") or 500),
        custom_min_days=int(data.get("custom_min_days") or 1),
        custom_max_days=int(data.get("custom_max_days") or 365),
        custom_base_ip=int(data.get("custom_base_ip") or 1),
        custom_group_ids=group_ids,
    )
    await state.clear()
    await event.answer(t(lang, "admin_custom_saved"))
    await _render_admin_shop(event, db, admin)


async def _render_payments(event: types.CallbackQuery, db: AsyncSession, admin: AdminDetails):
    lang = await _lang(db, event.from_user.id)
    config = await get_shop_config_by_admin(db, admin.id)
    if config is None:
        config = await upsert_shop_config(db, admin.id)
    text = rich(
        lang,
        "admin_payments_home",
        callback=config.pay_callback_base_url or "—",
        card=t(lang, "yes") if config.pay_card_enabled else t(lang, "no"),
        zarinpal=t(lang, "yes") if config.pay_zarinpal_enabled else t(lang, "no"),
        idpay=t(lang, "yes") if config.pay_idpay_enabled else t(lang, "no"),
        nowpayments=t(lang, "yes") if config.pay_nowpayments_enabled else t(lang, "no"),
        paypal=t(lang, "yes") if config.pay_paypal_enabled else t(lang, "no"),
        stripe=t(lang, "yes") if config.pay_stripe_enabled else t(lang, "no"),
    )
    try:
        await event.message.edit_text(text, reply_markup=ShopAdminPaymentsKeyboard(lang, config).as_markup())
    except TelegramBadRequest:
        await event.message.answer(text, reply_markup=ShopAdminPaymentsKeyboard(lang, config).as_markup())
    await event.answer()


@router.callback_query(ShopAdminKeyboard.Callback.filter(ShopAdminAction.payments == F.action))
async def payments_home(event: types.CallbackQuery, db: AsyncSession, admin: AdminDetails):
    await _render_payments(event, db, admin)


@router.callback_query(ShopAdminKeyboard.Callback.filter(ShopAdminAction.toggle_pay == F.action))
async def toggle_payment_gateway(
    event: types.CallbackQuery, callback_data: ShopAdminKeyboard.Callback, db: AsyncSession, admin: AdminDetails
):
    lang = await _lang(db, event.from_user.id)
    config = await get_shop_config_by_admin(db, admin.id)
    gw_id = int(callback_data.id or 0)
    kwargs: dict = {}
    if gw_id == PAY_GW_CARD:
        kwargs["pay_card_enabled"] = not bool(config and config.pay_card_enabled)
    elif gw_id == PAY_GW_ZARINPAL:
        if config and not (config.pay_zarinpal_merchant_id or "").strip() and not config.pay_zarinpal_enabled:
            await event.answer(t(lang, "admin_pay_need_setup"), show_alert=True)
            return
        kwargs["pay_zarinpal_enabled"] = not bool(config and config.pay_zarinpal_enabled)
    elif gw_id == PAY_GW_IDPAY:
        if config and not (config.pay_idpay_api_key or "").strip() and not config.pay_idpay_enabled:
            await event.answer(t(lang, "admin_pay_need_setup"), show_alert=True)
            return
        kwargs["pay_idpay_enabled"] = not bool(config and config.pay_idpay_enabled)
    elif gw_id == PAY_GW_NOWPAYMENTS:
        if config and not (config.pay_nowpayments_api_key or "").strip() and not config.pay_nowpayments_enabled:
            await event.answer(t(lang, "admin_pay_need_setup"), show_alert=True)
            return
        kwargs["pay_nowpayments_enabled"] = not bool(config and config.pay_nowpayments_enabled)
    elif gw_id == PAY_GW_PAYPAL:
        if (
            config
            and not ((config.pay_paypal_client_id or "").strip() and (config.pay_paypal_client_secret or "").strip())
            and not config.pay_paypal_enabled
        ):
            await event.answer(t(lang, "admin_pay_need_setup"), show_alert=True)
            return
        kwargs["pay_paypal_enabled"] = not bool(config and config.pay_paypal_enabled)
    elif gw_id == PAY_GW_STRIPE:
        if config and not (config.pay_stripe_secret_key or "").strip() and not config.pay_stripe_enabled:
            await event.answer(t(lang, "admin_pay_need_setup"), show_alert=True)
            return
        kwargs["pay_stripe_enabled"] = not bool(config and config.pay_stripe_enabled)
    else:
        await event.answer()
        return
    await upsert_shop_config(db, admin.id, **kwargs)
    await event.answer(t(lang, "admin_pay_toggled"))
    await _render_payments(event, db, admin)


@router.callback_query(ShopAdminKeyboard.Callback.filter(ShopAdminAction.set_pay == F.action))
async def ask_payment_setup(
    event: types.CallbackQuery, callback_data: ShopAdminKeyboard.Callback, db: AsyncSession, state: FSMContext
):
    lang = await _lang(db, event.from_user.id)
    gw_id = int(callback_data.id or 0)
    prompts = {
        PAY_GW_ZARINPAL: "admin_ask_zarinpal_merchant",
        PAY_GW_IDPAY: "admin_ask_idpay_key",
        PAY_GW_NOWPAYMENTS: "admin_ask_nowpayments_key",
        PAY_GW_PAYPAL: "admin_ask_paypal_client_id",
        PAY_GW_STRIPE: "admin_ask_stripe_secret",
        PAY_GW_CALLBACK: "admin_ask_callback_url",
    }
    prompt = prompts.get(gw_id)
    if not prompt:
        await event.answer()
        return
    await state.set_state(forms.ShopAdminPayment.waiting_value)
    await state.update_data(lang=lang, pay_gw_id=gw_id)
    msg = await event.message.answer(t(lang, prompt))
    await add_to_messages_to_delete(state, msg)
    await event.answer()


@router.message(forms.ShopAdminPayment.waiting_value)
async def save_payment_value(event: types.Message, db: AsyncSession, state: FSMContext, admin: AdminDetails):
    data = await state.get_data()
    lang = data.get("lang", "fa")
    gw_id = int(data.get("pay_gw_id") or 0)
    raw = (event.text or "").strip()
    if gw_id == PAY_GW_CALLBACK:
        await upsert_shop_config(db, admin.id, pay_callback_base_url=raw)
        await state.clear()
        await event.answer(t(lang, "admin_pay_saved"))
        # re-open payments from a synthetic path
        config = await get_shop_config_by_admin(db, admin.id)
        text = rich(
            lang,
            "admin_payments_home",
            callback=(config.pay_callback_base_url if config else None) or "—",
            card=t(lang, "yes") if config and config.pay_card_enabled else t(lang, "no"),
            zarinpal=t(lang, "yes") if config and config.pay_zarinpal_enabled else t(lang, "no"),
            idpay=t(lang, "yes") if config and config.pay_idpay_enabled else t(lang, "no"),
            nowpayments=t(lang, "yes") if config and config.pay_nowpayments_enabled else t(lang, "no"),
            paypal=t(lang, "yes") if config and config.pay_paypal_enabled else t(lang, "no"),
            stripe=t(lang, "yes") if config and config.pay_stripe_enabled else t(lang, "no"),
        )
        await event.answer(text, reply_markup=ShopAdminPaymentsKeyboard(lang, config).as_markup())
        return
    if gw_id == PAY_GW_ZARINPAL:
        await upsert_shop_config(db, admin.id, pay_zarinpal_merchant_id=raw, pay_zarinpal_enabled=True)
        await state.clear()
        await event.answer(t(lang, "admin_pay_saved"))
        return
    if gw_id == PAY_GW_IDPAY:
        await upsert_shop_config(db, admin.id, pay_idpay_api_key=raw, pay_idpay_enabled=True)
        await state.clear()
        await event.answer(t(lang, "admin_pay_saved"))
        return
    if gw_id == PAY_GW_NOWPAYMENTS:
        await state.update_data(pay_nowpayments_api_key=raw)
        await state.set_state(forms.ShopAdminPayment.waiting_value2)
        await event.answer(t(lang, "admin_ask_nowpayments_ipn"))
        return
    if gw_id == PAY_GW_PAYPAL:
        await state.update_data(pay_paypal_client_id=raw)
        await state.set_state(forms.ShopAdminPayment.waiting_value2)
        await event.answer(t(lang, "admin_ask_paypal_secret"))
        return
    if gw_id == PAY_GW_STRIPE:
        await state.update_data(pay_stripe_secret_key=raw)
        await state.set_state(forms.ShopAdminPayment.waiting_value2)
        await event.answer(t(lang, "admin_ask_stripe_webhook"))
        return
    await state.clear()
    await event.answer(t(lang, "admin_pay_saved"))


@router.message(forms.ShopAdminPayment.waiting_value2)
async def save_payment_value2(event: types.Message, db: AsyncSession, state: FSMContext, admin: AdminDetails):
    data = await state.get_data()
    lang = data.get("lang", "fa")
    gw_id = int(data.get("pay_gw_id") or 0)
    raw = (event.text or "").strip()
    if gw_id == PAY_GW_NOWPAYMENTS:
        await upsert_shop_config(
            db,
            admin.id,
            pay_nowpayments_api_key=data.get("pay_nowpayments_api_key"),
            pay_nowpayments_ipn_secret=raw,
            pay_nowpayments_enabled=True,
        )
    elif gw_id == PAY_GW_PAYPAL:
        await upsert_shop_config(
            db,
            admin.id,
            pay_paypal_client_id=data.get("pay_paypal_client_id"),
            pay_paypal_client_secret=raw,
            pay_paypal_enabled=True,
        )
    elif gw_id == PAY_GW_STRIPE:
        await upsert_shop_config(
            db,
            admin.id,
            pay_stripe_secret_key=data.get("pay_stripe_secret_key"),
            pay_stripe_webhook_secret=raw,
            pay_stripe_enabled=True,
        )
    await state.clear()
    await event.answer(t(lang, "admin_pay_saved"))


@router.callback_query(ShopAdminKeyboard.Callback.filter(ShopAdminAction.set_welcome == F.action))
async def ask_welcome(event: types.CallbackQuery, db: AsyncSession, state: FSMContext):
    lang = await _lang(db, event.from_user.id)
    await state.set_state(forms.ShopAdminWelcome.waiting_text)
    await state.update_data(lang=lang)
    msg = await event.message.answer(t(lang, "admin_ask_welcome"))
    await add_to_messages_to_delete(state, msg)
    await event.answer()


@router.message(forms.ShopAdminWelcome.waiting_text)
async def save_welcome(event: types.Message, db: AsyncSession, state: FSMContext, admin: AdminDetails):
    data = await state.get_data()
    lang = data.get("lang", "fa")
    raw = event.text.strip()
    welcome = None if raw in ("-", "") else raw[:500]
    await upsert_shop_config(db, admin.id, welcome_note="" if welcome is None else welcome)
    await state.clear()
    await event.answer(t(lang, "admin_welcome_saved"))
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
        data_limit = parse_gb_input(event.text)
    except ValueError:
        await event.answer(t(lang, "invalid_number"))
        return
    await state.update_data(data_limit=data_limit)
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
    try:
        group_ids = [int(x.strip()) for x in raw.split(",") if x.strip()]
    except ValueError:
        await event.answer(t(lang, "invalid_number"))
        return
    if not group_ids:
        await event.answer(t(lang, "admin_plan_groups_required"))
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


@router.callback_query(ShopAdminKeyboard.Callback.filter(ShopAdminAction.edit_plan == F.action))
async def edit_plan(event: types.CallbackQuery, callback_data: ShopAdminKeyboard.Callback, db: AsyncSession, admin: AdminDetails):
    await _render_plan_edit(event, db, admin, callback_data.id)


@router.callback_query(ShopAdminKeyboard.Callback.filter(F.action.in_(set(PLAN_EDIT_FIELDS))))
async def ask_edit_plan_field(
    event: types.CallbackQuery,
    callback_data: ShopAdminKeyboard.Callback,
    db: AsyncSession,
    state: FSMContext,
    admin: AdminDetails,
):
    lang = await _lang(db, event.from_user.id)
    plan = await get_shop_plan(db, callback_data.id)
    if not plan or plan.admin_id != admin.id:
        await event.answer("!", show_alert=True)
        return
    field, prompt_key = PLAN_EDIT_FIELDS[callback_data.action]
    await state.set_state(forms.ShopAdminPlanEdit.waiting_value)
    await state.update_data(lang=lang, plan_id=plan.id, field=field)
    current = _plan_field_current(lang, plan, field)
    msg = await event.message.answer(t(lang, prompt_key, current=current))
    await add_to_messages_to_delete(state, msg)
    await event.answer()


@router.message(forms.ShopAdminPlanEdit.waiting_value)
async def save_edit_plan_field(event: types.Message, db: AsyncSession, state: FSMContext, admin: AdminDetails):
    data = await state.get_data()
    lang = data.get("lang", "fa")
    plan = await get_shop_plan(db, data.get("plan_id"))
    if not plan or plan.admin_id != admin.id:
        await state.clear()
        return
    field = data.get("field")
    raw = event.text.strip()
    try:
        updates = _parse_plan_field_update(field, raw)
    except ValueError:
        await event.answer(t(lang, "invalid_number"))
        return
    await update_shop_plan(db, plan, **updates)
    await state.clear()
    await event.answer(t(lang, "admin_plan_updated"))
    await _render_plan_edit(event, db, admin, plan.id)


def _parse_plan_field_update(field: str, raw: str) -> dict:
    if field == "name":
        name = raw.strip()
        if not name:
            raise ValueError
        return {"name": name[:64]}
    if field == "data_limit":
        try:
            data_limit = parse_gb_input(raw)
        except ValueError:
            raise ValueError
        return {"data_limit": data_limit}
    if field == "expire_days":
        days = int(raw.strip())
        if days < 0:
            raise ValueError
        return {"expire_days": days}
    if field == "price_toman":
        price = int(raw.strip().replace(",", "").replace("٬", ""))
        if price < 0:
            raise ValueError
        return {"price_toman": price}
    if field == "group_ids":
        group_ids = [int(x.strip()) for x in raw.split(",") if x.strip()]
        if not group_ids:
            raise ValueError
        return {"group_ids": group_ids}
    if field == "ip_limit":
        ip_limit = parse_optional_limit(raw)
        if ip_limit == 0:
            raise ValueError
        return {"ip_limit": ip_limit}
    if field == "hwid_limit":
        return {"hwid_limit": parse_optional_limit(raw)}
    raise ValueError


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
            "admin_new_renewal" if (getattr(order, "order_kind", None) or "purchase") == "renewal" else "admin_new_order",
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

    from app.operation.shop import ShopOperation

    shop_op = ShopOperation(OperatorType.TELEGRAM)
    try:
        result = await shop_op.approve_order(db, admin, order.id)
    except Exception as exc:
        detail = getattr(exc, "detail", None) or str(exc)
        await event.answer(str(detail)[:180], show_alert=True)
        return

    is_renewal = (getattr(order, "order_kind", None) or "purchase") == "renewal"
    ok_key = "admin_renewed" if is_renewal else "admin_approved"
    await event.answer(t(lang, ok_key, username=result.username))
    try:
        mark = "🔄" if is_renewal else "✅"
        await event.message.edit_caption(caption=(event.message.caption or "") + f"\n\n{mark} {result.username}")
    except TelegramBadRequest:
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
    buyer_id = callback_data.id
    from app.db.crud.shop import claim_support_ticket, support_reply_allowed

    allowed, handler_username = await support_reply_allowed(db, buyer_id, admin.id)
    if not allowed:
        if handler_username:
            await event.answer(t(lang, "support_already_handled", admin=handler_username), show_alert=True)
        else:
            await event.answer(t(lang, "support_closed"), show_alert=True)
        return

    claimed = await claim_support_ticket(
        db,
        buyer_id,
        admin_id=admin.id,
        admin_username=admin.username,
    )
    if claimed is None:
        await event.answer(t(lang, "support_already_handled", admin=handler_username or "?"), show_alert=True)
        return

    from app.telegram import get_bot

    bot = get_bot()
    if bot:
        from app.telegram.utils.shop_helpers import notify_admins_support_claimed

        await notify_admins_support_claimed(db, bot=bot, buyer_telegram_id=buyer_id, handler=admin)

    await state.set_state(forms.ShopSupportAdmin.waiting_reply)
    await state.update_data(lang=lang, buyer_telegram_id=buyer_id)
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

    from app.db.crud.admin import build_admin_details, get_admin_by_id
    from app.db.crud.shop import close_support_ticket
    from app.telegram.utils.shop_helpers import notify_admins_support_closed

    db_admin = await get_admin_by_id(db, admin.id, load_users=False, load_usage_logs=False)
    admin_details = build_admin_details(db_admin, include_loaded_metrics=False)
    await close_support_ticket(
        db,
        buyer_id,
        admin_id=admin.id,
        admin_username=admin.username,
    )
    await notify_admins_support_closed(db, bot=bot, buyer_telegram_id=buyer_id, handler=admin_details)

    await state.clear()
    await event.answer(t(lang, "support_reply_sent"))
