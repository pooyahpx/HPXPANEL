from enum import Enum

from aiogram.filters.callback_data import CallbackData
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.db.models import ShopOrder, ShopPlan
from app.telegram.utils.i18n import format_bytes, format_price, t


class LangAction(str, Enum):
    fa = "fa"
    en = "en"


class LangKeyboard(InlineKeyboardBuilder):
    class Callback(CallbackData, prefix="lang"):
        code: str

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.button(text="🇮🇷 فارسی", callback_data=self.Callback(code="fa"))
        self.button(text="🇬🇧 English", callback_data=self.Callback(code="en"))
        self.adjust(2)


class ShopAction(str, Enum):
    home = "home"
    plans = "plans"
    buy = "buy"
    my_orders = "orders"
    lang = "lang"
    support = "support"
    back = "back"


class ShopKeyboard(InlineKeyboardBuilder):
    class Callback(CallbackData, prefix="shop"):
        action: ShopAction
        plan_id: int = 0

    def __init__(self, lang: str, plans: list[ShopPlan] | None = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for plan in plans or []:
            label = f"{plan.name} · {format_price(plan.price_toman)}T"
            self.button(text=label, callback_data=self.Callback(action=ShopAction.buy, plan_id=plan.id))
        self.button(text=t(lang, "btn_my_orders"), callback_data=self.Callback(action=ShopAction.my_orders))
        self.button(text=t(lang, "btn_support"), callback_data=self.Callback(action=ShopAction.support))
        self.button(text=t(lang, "btn_lang"), callback_data=self.Callback(action=ShopAction.lang))
        n = len(plans or [])
        if n:
            self.adjust(*([1] * n), 2, 1)
        else:
            self.adjust(2, 1)


class ShopHomeKeyboard(InlineKeyboardBuilder):
    class Callback(CallbackData, prefix="shophome"):
        action: ShopAction

    def __init__(self, lang: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.button(text=t(lang, "btn_shop"), callback_data=ShopKeyboard.Callback(action=ShopAction.plans))
        self.button(text=t(lang, "btn_my_orders"), callback_data=ShopKeyboard.Callback(action=ShopAction.my_orders))
        self.button(text=t(lang, "btn_support"), callback_data=ShopKeyboard.Callback(action=ShopAction.support))
        self.button(text=t(lang, "btn_lang"), callback_data=ShopKeyboard.Callback(action=ShopAction.lang))
        self.adjust(1, 2, 1)


class ShopAdminAction(str, Enum):
    home = "home"
    toggle = "toggle"
    set_card = "card"
    set_card_note = "cnote"
    set_card_photos = "cphotos"
    clear_card_photos = "cphclr"
    add_plan = "add"
    list_plans = "list"
    pending = "pending"
    approve = "ok"
    reject = "no"
    toggle_plan = "tp"
    delete_plan = "dp"
    support_reply = "sreply"


class ShopAdminKeyboard(InlineKeyboardBuilder):
    class Callback(CallbackData, prefix="shopadm"):
        action: ShopAdminAction
        id: int = 0

    def __init__(self, lang: str, enabled: bool, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.button(
            text=t(lang, "btn_disable") if enabled else t(lang, "btn_enable"),
            callback_data=self.Callback(action=ShopAdminAction.toggle),
        )
        self.button(text=t(lang, "btn_set_card"), callback_data=self.Callback(action=ShopAdminAction.set_card))
        self.button(text=t(lang, "btn_card_note"), callback_data=self.Callback(action=ShopAdminAction.set_card_note))
        self.button(text=t(lang, "btn_card_photos"), callback_data=self.Callback(action=ShopAdminAction.set_card_photos))
        self.button(text=t(lang, "btn_add_plan"), callback_data=self.Callback(action=ShopAdminAction.add_plan))
        self.button(text=t(lang, "btn_list_plans"), callback_data=self.Callback(action=ShopAdminAction.list_plans))
        self.button(text=t(lang, "btn_pending"), callback_data=self.Callback(action=ShopAdminAction.pending))
        self.button(text=t(lang, "btn_back"), callback_data=self.Callback(action=ShopAdminAction.home, id=-1))
        self.adjust(2, 2, 2, 1, 1)


class ShopAdminPlansKeyboard(InlineKeyboardBuilder):
    def __init__(self, lang: str, plans: list[ShopPlan], *args, **kwargs):
        super().__init__(*args, **kwargs)
        for plan in plans:
            state = t(lang, "active") if plan.is_active else t(lang, "inactive")
            self.button(
                text=f"{plan.name} ({state})",
                callback_data=ShopAdminKeyboard.Callback(action=ShopAdminAction.toggle_plan, id=plan.id),
            )
            self.button(
                text=t(lang, "btn_delete"),
                callback_data=ShopAdminKeyboard.Callback(action=ShopAdminAction.delete_plan, id=plan.id),
            )
        self.button(text=t(lang, "btn_back"), callback_data=ShopAdminKeyboard.Callback(action=ShopAdminAction.home))
        if not plans:
            self.adjust(1)
            return
        rows: list[int] = []
        for _ in plans:
            rows.extend([1, 1])
        rows.append(1)
        self.adjust(*rows)


class ShopOrderAdminKeyboard(InlineKeyboardBuilder):
    def __init__(self, lang: str, order: ShopOrder, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.button(
            text=t(lang, "btn_approve"),
            callback_data=ShopAdminKeyboard.Callback(action=ShopAdminAction.approve, id=order.id),
        )
        self.button(
            text=t(lang, "btn_reject"),
            callback_data=ShopAdminKeyboard.Callback(action=ShopAdminAction.reject, id=order.id),
        )
        self.adjust(2)


class SupportReplyKeyboard(InlineKeyboardBuilder):
    def __init__(self, lang: str, buyer_telegram_id: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.button(
            text=t(lang, "btn_support_reply"),
            callback_data=ShopAdminKeyboard.Callback(action=ShopAdminAction.support_reply, id=buyer_telegram_id),
        )
