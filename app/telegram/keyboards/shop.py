from enum import Enum

from aiogram.filters.callback_data import CallbackData
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.db.models import ShopOrder, ShopPlan
from app.telegram.utils.i18n import format_price, t


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
    test = "test"
    back = "back"


class ShopKeyboardCallback(CallbackData, prefix="shop"):
    action: ShopAction
    plan_id: int = 0


class ShopHomeKeyboard(InlineKeyboardBuilder):
    class Callback(CallbackData, prefix="shophome"):
        action: ShopAction

    def __init__(self, lang: str, show_test: bool = False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        cb = ShopKeyboardCallback
        self.button(text=t(lang, "btn_plans"), callback_data=cb(action=ShopAction.plans))
        if show_test:
            self.button(text=t(lang, "btn_test"), callback_data=cb(action=ShopAction.test))
        self.button(text=t(lang, "btn_my_orders"), callback_data=cb(action=ShopAction.my_orders))
        self.button(text=t(lang, "btn_support"), callback_data=cb(action=ShopAction.support))
        self.button(text=t(lang, "btn_lang"), callback_data=cb(action=ShopAction.lang))
        if show_test:
            self.adjust(1, 1, 2, 1)
        else:
            self.adjust(1, 2, 1)


class ShopPlansKeyboard(InlineKeyboardBuilder):
    """Plan list with prices — shown after tapping Plans."""

    def __init__(self, lang: str, plans: list[ShopPlan], *args, **kwargs):
        super().__init__(*args, **kwargs)
        cb = ShopKeyboardCallback
        for plan in plans:
            label = f"{plan.name} · {format_price(plan.price_toman)}T"
            self.button(text=label, callback_data=cb(action=ShopAction.buy, plan_id=plan.id))
        self.button(text=t(lang, "btn_back"), callback_data=cb(action=ShopAction.home))
        n = len(plans)
        if n:
            self.adjust(*([1] * n), 1)
        else:
            self.adjust(1)


class ShopKeyboard:
    """Backward-compatible namespace for shop callback filters."""

    Callback = ShopKeyboardCallback

class ShopAdminAction(str, Enum):
    home = "home"
    toggle = "toggle"
    set_card = "card"
    add_card = "acard"
    delete_card = "dcard"
    edit_card = "ecard"
    clear_cards = "ccard"
    set_card_note = "cnote"
    set_welcome = "welcome"
    set_card_photos = "cphotos"
    clear_card_photos = "cphclr"
    add_plan = "add"
    list_plans = "list"
    pending = "pending"
    approve = "ok"
    reject = "no"
    toggle_plan = "tp"
    delete_plan = "dp"
    edit_plan = "ep"
    plan_set_name = "psn"
    plan_set_gb = "psg"
    plan_set_days = "psd"
    plan_set_price = "psp"
    plan_set_groups = "psgr"
    plan_set_users = "psu"
    plan_set_hwid = "psh"
    support_reply = "sreply"
    toggle_test = "ttest"
    set_test = "stest"
    stats = "stats"


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
        self.button(text=t(lang, "btn_stats"), callback_data=self.Callback(action=ShopAdminAction.stats))
        self.button(text=t(lang, "btn_welcome"), callback_data=self.Callback(action=ShopAdminAction.set_welcome))
        self.button(text=t(lang, "btn_card_note"), callback_data=self.Callback(action=ShopAdminAction.set_card_note))
        self.button(text=t(lang, "btn_card_photos"), callback_data=self.Callback(action=ShopAdminAction.set_card_photos))
        self.button(text=t(lang, "btn_test_settings"), callback_data=self.Callback(action=ShopAdminAction.set_test))
        self.button(text=t(lang, "btn_toggle_test"), callback_data=self.Callback(action=ShopAdminAction.toggle_test))
        self.button(text=t(lang, "btn_add_plan"), callback_data=self.Callback(action=ShopAdminAction.add_plan))
        self.button(text=t(lang, "btn_list_plans"), callback_data=self.Callback(action=ShopAdminAction.list_plans))
        self.button(text=t(lang, "btn_pending"), callback_data=self.Callback(action=ShopAdminAction.pending))
        self.button(text=t(lang, "btn_back"), callback_data=self.Callback(action=ShopAdminAction.home, id=-1))
        self.adjust(2, 2, 2, 2, 2, 1, 1)


class ShopAdminCardsKeyboard(InlineKeyboardBuilder):
    def __init__(self, lang: str, cards: list[dict[str, str]], *args, **kwargs):
        super().__init__(*args, **kwargs)
        cb = ShopAdminKeyboard.Callback
        for index, card in enumerate(cards):
            number = card.get("number", "")
            label = f"{index + 1}. {number}"
            if len(label) > 28:
                label = label[:25] + "…"
            self.button(text=label, callback_data=cb(action=ShopAdminAction.edit_card, id=index))
            self.button(text=t(lang, "btn_delete"), callback_data=cb(action=ShopAdminAction.delete_card, id=index))
        if len(cards) < 3:
            self.button(text=t(lang, "btn_add_card"), callback_data=cb(action=ShopAdminAction.add_card))
        if cards:
            self.button(text=t(lang, "btn_clear_cards"), callback_data=cb(action=ShopAdminAction.clear_cards))
        self.button(text=t(lang, "btn_back"), callback_data=cb(action=ShopAdminAction.home))
        rows: list[int] = []
        for _ in cards:
            rows.append(2)
        if len(cards) < 3:
            rows.append(1)
        if cards:
            rows.append(1)
        rows.append(1)
        self.adjust(*rows)


class ShopAdminPlansKeyboard(InlineKeyboardBuilder):
    def __init__(self, lang: str, plans: list[ShopPlan], *args, **kwargs):
        super().__init__(*args, **kwargs)
        cb = ShopAdminKeyboard.Callback
        for plan in plans:
            state = t(lang, "active") if plan.is_active else t(lang, "inactive")
            self.button(
                text=f"✏️ {plan.name} ({state})",
                callback_data=cb(action=ShopAdminAction.edit_plan, id=plan.id),
            )
            self.button(
                text=t(lang, "btn_toggle_plan"),
                callback_data=cb(action=ShopAdminAction.toggle_plan, id=plan.id),
            )
            self.button(
                text=t(lang, "btn_delete"),
                callback_data=cb(action=ShopAdminAction.delete_plan, id=plan.id),
            )
        self.button(text=t(lang, "btn_back"), callback_data=cb(action=ShopAdminAction.home))
        if not plans:
            self.adjust(1)
            return
        rows: list[int] = []
        for _ in plans:
            rows.extend([1, 2])
        rows.append(1)
        self.adjust(*rows)


class ShopAdminPlanEditKeyboard(InlineKeyboardBuilder):
    PLAN_FIELD_ACTIONS = (
        ShopAdminAction.plan_set_name,
        ShopAdminAction.plan_set_gb,
        ShopAdminAction.plan_set_days,
        ShopAdminAction.plan_set_price,
        ShopAdminAction.plan_set_groups,
        ShopAdminAction.plan_set_users,
        ShopAdminAction.plan_set_hwid,
    )

    def __init__(self, lang: str, plan_id: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        cb = ShopAdminKeyboard.Callback
        labels = (
            "btn_edit_plan_name",
            "btn_edit_plan_gb",
            "btn_edit_plan_days",
            "btn_edit_plan_price",
            "btn_edit_plan_groups",
            "btn_edit_plan_users",
            "btn_edit_plan_hwid",
        )
        for action, label_key in zip(self.PLAN_FIELD_ACTIONS, labels, strict=True):
            self.button(text=t(lang, label_key), callback_data=cb(action=action, id=plan_id))
        self.button(text=t(lang, "btn_back"), callback_data=cb(action=ShopAdminAction.list_plans))
        self.adjust(2, 2, 2, 1, 1)


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
