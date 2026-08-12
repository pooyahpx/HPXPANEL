from aiogram import F, Router, types
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crud.shop import get_enabled_shop_config, get_telegram_lang
from app.models.admin import AdminDetails
from app.operation import OperatorType
from app.operation.system import SystemOperation
from app.settings import telegram_settings
from app.telegram.keyboards.base import CancelAction, CancelKeyboard
from app.telegram.keyboards.deck import DeckPanel
from app.telegram.keyboards.shop import LangKeyboard, ShopHomeKeyboard
from app.telegram.utils.i18n import t
from app.telegram.utils.shared import delete_messages
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

    await open_main_menu(message, db, admin, lang, edit=isinstance(event, types.CallbackQuery))
    if isinstance(event, types.CallbackQuery):
        await event.answer()
