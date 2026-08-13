from aiogram import F, Router, types
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crud.admin import build_admin_details, claim_owner_telegram_id, get_owner
from app.db.crud.shop import get_enabled_shop_config, get_telegram_lang
from app.models.admin import AdminDetails, verify_password
from app.operation import OperatorType
from app.operation.system import SystemOperation
from app.settings import telegram_settings
from app.telegram.keyboards.base import CancelAction, CancelKeyboard
from app.telegram.keyboards.deck import DeckPanel
from app.telegram.keyboards.shop import LangKeyboard, ShopHomeKeyboard
from app.telegram.utils import forms
from app.telegram.utils.i18n import t
from app.telegram.utils.shared import delete_messages
from app.telegram.utils.shop_helpers import notify_admins_user_joined
from app.telegram.utils.texts import Message as Texts

system_operator = SystemOperation(OperatorType.TELEGRAM)

router = Router(name="base")


async def open_main_menu(
    message: types.Message,
    db: AsyncSession,
    admin: AdminDetails | None,
    lang: str,
    *,
    edit: bool = False,
):
    from app.telegram.handlers.shop import render_shop_home

    settings = await telegram_settings()
    if admin:
        stats = await system_operator.get_system_stats(db, admin)
        text = Texts.deck_home(stats, admin)
        markup = DeckPanel(
            admin=admin,
            panel_url=settings.mini_app_web_url if settings.mini_app_login else None,
            lang=lang,
        ).as_markup()
        if edit:
            try:
                await message.edit_text(text=text, reply_markup=markup)
                return
            except TelegramBadRequest:
                pass
        await message.answer(text=text, reply_markup=markup)
        return

    config = await get_enabled_shop_config(db)
    if config and config.enabled:
        if edit:
            try:
                await message.delete()
            except TelegramBadRequest:
                pass
        await render_shop_home(message, db, lang)
        return

    text = t(lang, "shop_disabled")
    if not admin:
        text += "\n\n" + t(lang, "claim_hint")
    markup = ShopHomeKeyboard(lang).as_markup()
    if edit:
        try:
            await message.edit_text(text, reply_markup=markup)
            return
        except TelegramBadRequest:
            pass
    await message.answer(text, reply_markup=markup)


@router.callback_query(CancelKeyboard.Callback.filter(CancelAction.cancel == F.action))
@router.message(CommandStart())
async def command_start_handler(
    event: types.Message | types.CallbackQuery,
    admin: AdminDetails | None,
    state: FSMContext | None = None,
    db: AsyncSession | None = None,
):
    message = event.message if isinstance(event, types.CallbackQuery) else event

    if state is not None and (await state.get_state() is not None):
        await delete_messages(event, state)
        await state.clear()

    telegram_id = event.from_user.id
    lang = await get_telegram_lang(db, telegram_id)
    if not lang:
        await message.answer(t("en", "choose_lang"), reply_markup=LangKeyboard().as_markup())
        if isinstance(event, types.CallbackQuery):
            await event.answer()
        return

    # First /start after install: bind unbound panel owner to this Telegram user.
    if admin is None:
        claimed = await claim_owner_telegram_id(db, telegram_id, force=False)
        if claimed is not None:
            admin = build_admin_details(claimed, include_loaded_metrics=True)
            await message.answer(t(lang, "owner_claimed"))

    if admin is None and event.from_user:
        from app.telegram import get_bot

        bot = get_bot()
        await notify_admins_user_joined(db, bot, event.from_user)

    await open_main_menu(message, db, admin, lang, edit=isinstance(event, types.CallbackQuery))
    if isinstance(event, types.CallbackQuery):
        await event.answer()


@router.message(Command("claimowner"))
async def claim_owner_command(
    message: types.Message,
    admin: AdminDetails | None,
    state: FSMContext,
    db: AsyncSession,
):
    """Re-bind Telegram to panel owner using the owner panel password."""
    lang = (await get_telegram_lang(db, message.from_user.id)) or "fa"
    if admin and admin.is_owner:
        await message.answer(t(lang, "owner_claimed"))
        return
    await state.set_state(forms.ClaimOwner.waiting_password)
    await state.update_data(lang=lang)
    await message.answer(t(lang, "claim_ask_password"))


@router.message(forms.ClaimOwner.waiting_password)
async def claim_owner_password(message: types.Message, state: FSMContext, db: AsyncSession):
    data = await state.get_data()
    lang = data.get("lang", "fa")
    owner = await get_owner(db)
    if owner is None or not await verify_password(message.text or "", owner.hashed_password):
        await state.clear()
        await message.answer(t(lang, "claim_bad_password"))
        return

    claimed = await claim_owner_telegram_id(db, message.from_user.id, force=True)
    await state.clear()
    if claimed is None:
        await message.answer(t(lang, "claim_bad_password"))
        return
    await message.answer(t(lang, "claim_ok"))
