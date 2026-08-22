from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crud.admin import get_admin_by_id, get_admins_simple
from app.db.crud.admin_role import get_role, get_roles_simple
from app.models.admin import AdminDetails, AdminModify, AdminSimpleListQuery
from app.models.admin_role import AdminRoleModify, RolePermissions
from app.operation import OperatorType
from app.operation.admin import AdminOperation
from app.operation.admin_role import AdminRoleOperation
from app.telegram.keyboards.admin import AdminPanel, AdminPanelAction
from app.telegram.utils.filters import IsOwnerFilter
from app.telegram.utils.i18n import rich, t
from app.telegram.utils.permission_bot import (
    PERM_TOGGLE_ORDER,
    PERM_TOGGLE_SPECS,
    permission_enabled,
    permissions_as_dict,
    toggle_permission,
)

admin_operator = AdminOperation(OperatorType.TELEGRAM)
role_operator = AdminRoleOperation(OperatorType.TELEGRAM)

router = Router(name="permissions")


async def _lang(db: AsyncSession, telegram_id: int) -> str:
    from app.db.crud.shop import get_telegram_lang

    return (await get_telegram_lang(db, telegram_id)) or "fa"


def _perm_kb(lang: str, role_id: int):
    kb = InlineKeyboardBuilder()
    cb = AdminPanel.Callback
    for key in PERM_TOGGLE_ORDER:
        kb.button(text=t(lang, f"perm_{key}"), callback_data=cb(action=AdminPanelAction.perm_toggle, id=role_id, key=key))
    kb.button(text=t(lang, "btn_back"), callback_data=cb(action=AdminPanelAction.manage_permissions))
    kb.adjust(1)
    return kb.as_markup()


@router.callback_query(IsOwnerFilter(), AdminPanel.Callback.filter(AdminPanelAction.manage_permissions == F.action))
async def manage_permissions_home(event: CallbackQuery, db: AsyncSession):
    lang = await _lang(db, event.from_user.id)
    admin_rows, _ = await get_admins_simple(db, AdminSimpleListQuery(all=True), include_owner=False)

    kb = InlineKeyboardBuilder()
    cb = AdminPanel.Callback
    kb.button(text=t(lang, "perm_manage_roles"), callback_data=cb(action=AdminPanelAction.perm_roles))
    for admin_id, username in admin_rows:
        kb.button(
            text=f"👤 {username}",
            callback_data=cb(action=AdminPanelAction.perm_pick_admin, id=admin_id),
        )
    kb.button(text=t(lang, "btn_back"), callback_data=cb(action=AdminPanelAction.refresh))
    kb.adjust(1)

    text = rich(lang, "perm_home")
    try:
        await event.message.edit_text(text, reply_markup=kb.as_markup())
    except TelegramBadRequest:
        await event.message.answer(text, reply_markup=kb.as_markup())
    await event.answer()


@router.callback_query(IsOwnerFilter(), AdminPanel.Callback.filter(AdminPanelAction.perm_roles == F.action))
async def perm_roles_list(event: CallbackQuery, db: AsyncSession):
    lang = await _lang(db, event.from_user.id)
    roles = await get_roles_simple(db)
    kb = InlineKeyboardBuilder()
    cb = AdminPanel.Callback
    for role_id, name, is_owner in roles:
        if is_owner:
            continue
        kb.button(text=f"🛡 {name}", callback_data=cb(action=AdminPanelAction.perm_edit_role, id=role_id))
    kb.button(text=t(lang, "btn_back"), callback_data=cb(action=AdminPanelAction.manage_permissions))
    kb.adjust(1)
    text = rich(lang, "perm_roles_pick")
    try:
        await event.message.edit_text(text, reply_markup=kb.as_markup())
    except TelegramBadRequest:
        await event.message.answer(text, reply_markup=kb.as_markup())
    await event.answer()


@router.callback_query(IsOwnerFilter(), AdminPanel.Callback.filter(AdminPanelAction.perm_pick_admin == F.action))
async def perm_pick_admin(event: CallbackQuery, callback_data: AdminPanel.Callback, db: AsyncSession, admin: AdminDetails):
    lang = await _lang(db, event.from_user.id)
    target = await get_admin_by_id(db, callback_data.id, load_users=False, load_usage_logs=False, load_role=True)
    if target is None or target.role_id == 1:
        await event.answer("!", show_alert=True)
        return

    roles = await get_roles_simple(db)
    kb = InlineKeyboardBuilder()
    cb = AdminPanel.Callback
    current_role = target.role_id
    for role_id, name, is_owner in roles:
        if is_owner:
            continue
        prefix = "✅ " if role_id == current_role else ""
        kb.button(
            text=f"{prefix}{name}",
            callback_data=cb(action=AdminPanelAction.perm_set_role, id=target.id, key=str(role_id)),
        )
    kb.button(text=t(lang, "btn_back"), callback_data=cb(action=AdminPanelAction.manage_permissions))
    kb.adjust(1)
    role_name = target.role.name if target.role else "?"
    text = rich(lang, "perm_pick_role_for_admin", username=target.username, role=role_name)
    try:
        await event.message.edit_text(text, reply_markup=kb.as_markup())
    except TelegramBadRequest:
        await event.message.answer(text, reply_markup=kb.as_markup())
    await event.answer()


@router.callback_query(IsOwnerFilter(), AdminPanel.Callback.filter(AdminPanelAction.perm_set_role == F.action))
async def perm_set_role(
    event: CallbackQuery, callback_data: AdminPanel.Callback, db: AsyncSession, admin: AdminDetails
):
    lang = await _lang(db, event.from_user.id)
    try:
        role_id = int(callback_data.key)
    except (TypeError, ValueError):
        await event.answer("!", show_alert=True)
        return
    if role_id == 1:
        await event.answer(t(lang, "perm_owner_forbidden"), show_alert=True)
        return

    try:
        await admin_operator.modify_admin_by_id(
            db,
            callback_data.id,
            AdminModify(role_id=role_id),
            admin,
        )
    except Exception as exc:
        await event.answer(str(exc)[:180], show_alert=True)
        return

    await event.answer(t(lang, "perm_role_updated"), show_alert=True)
    await perm_pick_admin(
        event,
        AdminPanel.Callback(action=AdminPanelAction.perm_pick_admin, id=callback_data.id),
        db,
        admin,
    )


@router.callback_query(IsOwnerFilter(), AdminPanel.Callback.filter(AdminPanelAction.perm_edit_role == F.action))
async def perm_edit_role(event: CallbackQuery, callback_data: AdminPanel.Callback, db: AsyncSession):
    lang = await _lang(db, event.from_user.id)
    role = await get_role(db, callback_data.id)
    if role is None or role.is_owner:
        await event.answer("!", show_alert=True)
        return

    lines = [rich(lang, "perm_role_editor", role=role.name), ""]
    for key in PERM_TOGGLE_ORDER:
        resource, action, _ = PERM_TOGGLE_SPECS[key]
        enabled = permission_enabled(permissions_as_dict(role.permissions), resource, action)
        state = t(lang, "yes") if enabled else t(lang, "no")
        lines.append(f"{t(lang, f'perm_{key}')}: {state}")

    text = "\n".join(lines)
    try:
        await event.message.edit_text(text, reply_markup=_perm_kb(lang, role.id))
    except TelegramBadRequest:
        await event.message.answer(text, reply_markup=_perm_kb(lang, role.id))
    await event.answer()


@router.callback_query(IsOwnerFilter(), AdminPanel.Callback.filter(AdminPanelAction.perm_toggle == F.action))
async def perm_toggle(
    event: CallbackQuery, callback_data: AdminPanel.Callback, db: AsyncSession, admin: AdminDetails
):
    lang = await _lang(db, event.from_user.id)
    role = await get_role(db, callback_data.id)
    if role is None or role.is_owner or not callback_data.key:
        await event.answer("!", show_alert=True)
        return

    if callback_data.key not in PERM_TOGGLE_ORDER:
        await event.answer("!", show_alert=True)
        return

    new_permissions = toggle_permission(permissions_as_dict(role.permissions), callback_data.key)
    try:
        await role_operator.modify_role(
            db,
            role.id,
            AdminRoleModify(permissions=RolePermissions.model_validate(new_permissions)),
            admin,
        )
    except Exception as exc:
        await event.answer(str(exc)[:180], show_alert=True)
        return

    await event.answer(t(lang, "perm_updated"))
    await perm_edit_role(
        event,
        AdminPanel.Callback(action=AdminPanelAction.perm_edit_role, id=role.id),
        db,
    )
