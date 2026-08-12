"""HPXPANEL Telegram deck — tile-style inline keyboard layout."""

from aiogram.utils.keyboard import InlineKeyboardBuilder, WebAppInfo

from app.models.admin import AdminDetails
from app.operation.permissions import PermissionDenied, enforce_permission, is_scope_all
from app.telegram.keyboards.admin import AdminPanelAction
from app.telegram.utils.i18n import t
from app.telegram.utils.texts import Button as Texts


def _has_permission(admin: AdminDetails | None, resource: str, action: str) -> bool:
    if not admin:
        return False
    try:
        enforce_permission(admin, resource, action)
        return True
    except PermissionDenied:
        return False


class DeckPanel(InlineKeyboardBuilder):
    """Role-aware main menu with 2-column glass-style tile buttons."""

    def __init__(
        self,
        admin: AdminDetails | None = None,
        panel_url: str | None = None,
        lang: str = "en",
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        from app.telegram.keyboards.admin import AdminPanel

        panel_cb = AdminPanel.Callback
        rows: list[int] = []

        if panel_url and panel_url.startswith("https://"):
            self.button(text=Texts.open_panel, web_app=WebAppInfo(url=panel_url))
            rows.append(1)

        can_read_users = _has_permission(admin, "users", "read")
        can_create_users = _has_permission(admin, "users", "create")
        can_read_nodes = _has_permission(admin, "nodes", "reconnect")
        can_bulk = is_scope_all(admin, "users", "update") if admin else False

        tile_count = 0
        if can_read_users:
            self.button(text=Texts.users, switch_inline_query_current_chat="")
            tile_count += 1
        self.button(text=Texts.refresh_data, callback_data=panel_cb(action=AdminPanelAction.refresh))
        tile_count += 1
        if tile_count == 2:
            rows.append(2)
        elif tile_count == 1:
            rows.append(1)

        create_count = 0
        if can_create_users:
            self.button(text=Texts.create_user, callback_data=panel_cb(action=AdminPanelAction.create_user))
            create_count += 1
            self.button(
                text=Texts.create_user_from_template,
                callback_data=panel_cb(action=AdminPanelAction.create_user_from_template),
            )
            create_count += 1
        if create_count == 2:
            rows.append(2)
        elif create_count == 1:
            rows.append(1)

        fleet_count = 0
        if can_read_nodes:
            self.button(text=Texts.sync_users, callback_data=panel_cb(action=AdminPanelAction.sync_users))
            fleet_count += 1
            self.button(
                text=Texts.reconnect_all_nodes,
                callback_data=panel_cb(action=AdminPanelAction.reconnect_all_nodes),
            )
            fleet_count += 1
        if fleet_count == 2:
            rows.append(2)
        elif fleet_count == 1:
            rows.append(1)

        if can_bulk:
            self.button(text=Texts.bulk_actions, callback_data=panel_cb(action=AdminPanelAction.bulk_actions))
            rows.append(1)

        # Shop management (any panel admin)
        self.button(
            text=t(lang, "btn_admin_shop"),
            callback_data=panel_cb(action=AdminPanelAction.shop_manage),
        )
        rows.append(1)

        if rows:
            self.adjust(*rows)
