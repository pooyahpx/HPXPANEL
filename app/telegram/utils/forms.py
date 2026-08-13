from aiogram.fsm.state import State, StatesGroup


class CreateUser(StatesGroup):
    username = State()
    data_limit = State()
    expire = State()
    status = State()
    on_hold_timeout = State()
    group_ids = State()


class CreateUserFromTemplate(StatesGroup):
    username = State()


class DeleteExpired(StatesGroup):
    expired_before = State()


class BulkModify(StatesGroup):
    expiry = State()
    data_limit = State()


class BulkCreateFromTemplate(StatesGroup):
    count = State()
    strategy = State()
    username = State()
    start_number = State()


class ModifyUser(StatesGroup):
    new_data_limit = State()
    new_expiry = State()
    new_note = State()


class ShopAdminCard(StatesGroup):
    card_number = State()
    card_holder = State()


class ShopAdminPlan(StatesGroup):
    name = State()
    gb = State()
    days = State()
    price = State()
    groups = State()
    ip_limit = State()
    hwid_limit = State()


class ShopBuy(StatesGroup):
    waiting_receipt = State()


class ShopSupport(StatesGroup):
    waiting_message = State()


class ShopSupportAdmin(StatesGroup):
    waiting_reply = State()


class ShopAdminCardNote(StatesGroup):
    waiting_text = State()


class ShopAdminCardPhotos(StatesGroup):
    waiting_photos = State()


class PromoteAdmin(StatesGroup):
    waiting_target = State()


class ClaimOwner(StatesGroup):
    waiting_password = State()
