from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crud.admin import get_admin, get_admin_by_telegram_id
from app.models.admin import AdminDetails, AdminModify
from app.models.node import NodeListQuery
from app.operation import OperatorType
from app.operation.admin import AdminOperation
from app.operation.node import NodeOperation
from app.operation.system import SystemOperation
from app.settings import telegram_settings
from app.telegram.keyboards.admin import AdminPanel, AdminPanelAction
from app.telegram.keyboards.deck import DeckPanel
from app.telegram.utils import forms
from app.telegram.utils.filters import HasPermission, IsAdminFilter, IsOwnerFilter
from app.telegram.utils.i18n import rich, t
from app.telegram.utils.shared import add_to_messages_to_delete
from app.telegram.utils.texts import Message as Texts

system_operator = SystemOperation(OperatorType.TELEGRAM)
node_operator = NodeOperation(OperatorType.TELEGRAM)
admin_operator = AdminOperation(OperatorType.TELEGRAM)

router = Router(name="main_menu")


async def _lang(db: AsyncSession, telegram_id: int) -> str:
    from app.db.crud.shop import get_telegram_lang

    return (await get_telegram_lang(db, telegram_id)) or "fa"


async def _render_main_menu(event: CallbackQuery, db: AsyncSession, admin: AdminDetails):
    """Render the main admin panel with permission-aware keyboard."""
    stats = await system_operator.get_system_stats(db, admin)
    settings = await telegram_settings()
    lang = await _lang(db, event.from_user.id)
    return DeckPanel(
        admin=admin,
        panel_url=settings.mini_app_web_url if settings.mini_app_login else None,
        lang=lang,
    ).as_markup(), Texts.deck_home(stats, admin)


@router.callback_query(IsAdminFilter(), AdminPanel.Callback.filter(AdminPanelAction.refresh == F.action))
async def reload_data(event: CallbackQuery, db: AsyncSession, admin: AdminDetails):
    markup, text = await _render_main_menu(event, db, admin)
    try:
        await event.message.edit_text(text=text, reply_markup=markup)
    except TelegramBadRequest:
        pass
    await event.answer(Texts.refreshed)


@router.callback_query(IsAdminFilter(), AdminPanel.Callback.filter(AdminPanelAction.shop_manage == F.action))
async def open_shop_manage(event: CallbackQuery, db: AsyncSession, admin: AdminDetails):
    from app.telegram.handlers.shop_admin import _render_admin_shop

    await _render_admin_shop(event, db, admin)


@router.callback_query(IsOwnerFilter(), AdminPanel.Callback.filter(AdminPanelAction.promote_admin == F.action))
async def ask_promote_admin(event: CallbackQuery, db: AsyncSession, state: FSMContext):
    lang = await _lang(db, event.from_user.id)
    await state.set_state(forms.PromoteAdmin.waiting_target)
    await state.update_data(lang=lang)
    msg = await event.message.answer(t(lang, "promote_ask_target"))
    await add_to_messages_to_delete(state, msg)
    await event.answer()


@router.message(IsOwnerFilter(), forms.PromoteAdmin.waiting_target)
async def promote_admin_target(event: Message, db: AsyncSession, state: FSMContext, admin: AdminDetails):
    data = await state.get_data()
    lang = data.get("lang", "fa")

    target_id: int | None = None
    if event.forward_from is not None:
        target_id = event.forward_from.id
    elif event.text:
        raw = event.text.strip()
        if raw.isdigit():
            target_id = int(raw)

    if not target_id:
        await event.answer(t(lang, "invalid_number"))
        return

    existing = await get_admin_by_telegram_id(db, target_id, load_users=False, load_usage_logs=False)
    if existing:
        await state.clear()
        await event.answer(t(lang, "promote_exists", username=existing.username))
        return

    await state.update_data(target_telegram_id=target_id)
    await state.set_state(forms.PromoteAdmin.waiting_username)
    msg = await event.message.answer(t(lang, "promote_ask_username"))
    await add_to_messages_to_delete(state, msg)


@router.message(IsOwnerFilter(), forms.PromoteAdmin.waiting_username)
async def promote_admin_username(event: Message, db: AsyncSession, state: FSMContext, admin: AdminDetails):
    data = await state.get_data()
    lang = data.get("lang", "fa")
    target_id = data.get("target_telegram_id")

    if not target_id or not event.text:
        await state.clear()
        await event.answer(t(lang, "promote_fail", error="missing data"))
        return

    username = event.text.strip()
    if not username:
        await event.answer(t(lang, "promote_panel_not_found"))
        return

    panel_admin = await get_admin(db, username, load_users=False, load_usage_logs=False)
    if panel_admin is None:
        await event.answer(t(lang, "promote_panel_not_found"))
        return

    if panel_admin.role_id == 1:
        await state.clear()
        await event.answer(t(lang, "promote_owner_forbidden"))
        return

    if panel_admin.telegram_id is not None:
        await state.clear()
        await event.answer(t(lang, "promote_panel_linked"))
        return

    try:
        await admin_operator.modify_admin_by_id(
            db,
            panel_admin.id,
            AdminModify(telegram_id=int(target_id)),
            admin,
        )
    except Exception as exc:
        await state.clear()
        await event.answer(t(lang, "promote_fail", error=str(exc)))
        return

    await state.clear()
    await event.answer(rich(lang, "promote_ok", username=panel_admin.username))


@router.callback_query(
    HasPermission("nodes", "reconnect"),
    AdminPanel.Callback.filter(AdminPanelAction.sync_users == F.action),
)
async def sync_users(event: CallbackQuery, db: AsyncSession, admin: AdminDetails):
    await event.answer(Texts.syncing)
    nodes_response = await node_operator.get_db_nodes(db, NodeListQuery())
    for node in nodes_response.nodes:
        await node_operator.sync_node_users(db, node.id, flush_users=True)
    markup, text = await _render_main_menu(event, db, admin)
    try:
        await event.message.edit_text(text=text, reply_markup=markup)
    except TelegramBadRequest:
        pass
    await event.answer(Texts.synced)


@router.callback_query(
    HasPermission("nodes", "reconnect"),
    AdminPanel.Callback.filter(AdminPanelAction.reconnect_all_nodes == F.action),
)
async def reconnect_all_nodes(event: CallbackQuery, db: AsyncSession, admin: AdminDetails):
    await event.answer(Texts.reconnecting_nodes)
    await node_operator.restart_all_node(db=db, admin=admin)
    markup, text = await _render_main_menu(event, db, admin)
    try:
        await event.message.edit_text(text=text, reply_markup=markup)
    except TelegramBadRequest:
        pass
    await event.answer(Texts.nodes_reconnected)
