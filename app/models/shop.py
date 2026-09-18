from datetime import datetime as dt
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ShopOrderKindLiteral(str, Enum):
    purchase = "purchase"
    renewal = "renewal"


class ShopOrderStatusLiteral(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class ShopCard(BaseModel):
    number: str = Field(min_length=1, max_length=64)
    holder: str = Field(default="", max_length=128)


class ShopConfigResponse(BaseModel):
    id: int
    admin_id: int
    enabled: bool
    card_number: str | None = None
    card_holder: str | None = None
    card_note: str | None = None
    card_photos: list[str] = Field(default_factory=list)
    welcome_note: str | None = None
    cards: list[ShopCard] = Field(default_factory=list)
    test_enabled: bool = False
    test_data_limit: int = 0
    test_expire_days: int = 1
    test_group_ids: list[int] = Field(default_factory=list)
    custom_enabled: bool = False
    custom_price_per_gb: int = 0
    custom_price_per_day: int = 0
    custom_price_per_ip: int = 0
    custom_min_gb: int = 1
    custom_max_gb: int = 500
    custom_min_days: int = 1
    custom_max_days: int = 365
    custom_base_ip: int = 1
    custom_group_ids: list[int] = Field(default_factory=list)
    created_at: dt | None = None

    model_config = ConfigDict(from_attributes=True)


class ShopConfigUpdate(BaseModel):
    enabled: bool | None = None
    card_note: str | None = None
    welcome_note: str | None = None
    cards: list[ShopCard] | None = None
    test_enabled: bool | None = None
    test_data_limit: int | None = Field(default=None, ge=0)
    test_expire_days: int | None = Field(default=None, ge=0)
    test_group_ids: list[int] | None = None
    custom_enabled: bool | None = None
    custom_price_per_gb: int | None = Field(default=None, ge=0)
    custom_price_per_day: int | None = Field(default=None, ge=0)
    custom_price_per_ip: int | None = Field(default=None, ge=0)
    custom_min_gb: int | None = Field(default=None, ge=1)
    custom_max_gb: int | None = Field(default=None, ge=1)
    custom_min_days: int | None = Field(default=None, ge=1)
    custom_max_days: int | None = Field(default=None, ge=1)
    custom_base_ip: int | None = Field(default=None, ge=1)
    custom_group_ids: list[int] | None = None

    @model_validator(mode="after")
    def validate_custom_groups_and_bounds(self):
        if self.custom_enabled is True:
            groups = self.custom_group_ids
            if groups is not None and not groups:
                raise ValueError("you must select at least one group for custom purchase")
        if (
            self.custom_min_gb is not None
            and self.custom_max_gb is not None
            and self.custom_min_gb > self.custom_max_gb
        ):
            raise ValueError("custom_min_gb cannot exceed custom_max_gb")
        if (
            self.custom_min_days is not None
            and self.custom_max_days is not None
            and self.custom_min_days > self.custom_max_days
        ):
            raise ValueError("custom_min_days cannot exceed custom_max_days")
        return self


class ShopPlanResponse(BaseModel):
    id: int
    admin_id: int
    name: str
    data_limit: int
    expire_days: int
    price_toman: int
    group_ids: list[int] = Field(default_factory=list)
    ip_limit: int | None = None
    hwid_limit: int | None = None
    is_active: bool = True
    created_at: dt | None = None

    model_config = ConfigDict(from_attributes=True)


class ShopPlanCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    data_limit: int = Field(default=0, ge=0)
    expire_days: int = Field(default=30, ge=0)
    price_toman: int = Field(default=0, ge=0)
    group_ids: list[int] = Field(min_length=1)
    ip_limit: int | None = Field(default=None, ge=0)
    hwid_limit: int | None = Field(default=None, ge=0)
    is_active: bool = True

    @field_validator("group_ids")
    @classmethod
    def require_at_least_one_group(cls, value: list[int]) -> list[int]:
        if not value:
            raise ValueError("you must select at least one group")
        return value


class ShopPlanUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=64)
    data_limit: int | None = Field(default=None, ge=0)
    expire_days: int | None = Field(default=None, ge=0)
    price_toman: int | None = Field(default=None, ge=0)
    group_ids: list[int] | None = None
    ip_limit: int | None = Field(default=None, ge=0)
    hwid_limit: int | None = Field(default=None, ge=0)
    is_active: bool | None = None

    @field_validator("group_ids")
    @classmethod
    def require_at_least_one_group_when_set(cls, value: list[int] | None) -> list[int] | None:
        if value is not None and not value:
            raise ValueError("you must select at least one group")
        return value


class ShopOrderResponse(BaseModel):
    id: int
    plan_id: int | None = None
    admin_id: int
    buyer_telegram_id: int
    buyer_username: str | None = None
    status: ShopOrderStatusLiteral
    order_kind: ShopOrderKindLiteral = ShopOrderKindLiteral.purchase
    renew_user_id: int | None = None
    renew_username: str | None = None
    receipt_file_id: str | None = None
    has_receipt: bool = False
    created_user_id: int | None = None
    created_username: str | None = None
    plan_name: str | None = None
    plan_price_toman: int | None = None
    requested_username: str | None = None
    custom_data_gb: int | None = None
    custom_expire_days: int | None = None
    custom_ip_limit: int | None = None
    quoted_price_toman: int | None = None
    is_custom: bool = False
    note: str | None = None
    created_at: dt | None = None

    model_config = ConfigDict(from_attributes=True)


class ShopOrderListResponse(BaseModel):
    orders: list[ShopOrderResponse]
    total: int


class ShopOrderRejectRequest(BaseModel):
    note: str | None = Field(default=None, max_length=500)


class ShopStatsResponse(BaseModel):
    total_buyers: int = 0
    joined: int = 0
    test_claimed: int = 0
    test_accounts: int = 0
    test_used_bytes: int = 0
    orders_pending: int = 0
    orders_approved: int = 0
    orders_rejected: int = 0
    orders_renewed: int = 0


class ShopApproveResponse(BaseModel):
    order: ShopOrderResponse
    username: str
    subscription_url: str | None = None


class CreateBudgetLedgerEntry(BaseModel):
    id: int
    admin_id: int
    admin_username: str | None = None
    entry_type: str
    amount_toman: int
    balance_after: int
    actor_admin_id: int | None = None
    user_id: int | None = None
    username: str | None = None
    billable_gb: int = 0
    billable_days: int = 0
    price_per_gb: int | None = None
    price_per_day: int | None = None
    pricing_mode: str | None = None
    tier_gb: int | None = None
    detail: str | None = None
    settled_with_owner: bool = False
    settled_at: dt | None = None
    settled_by_admin_id: int | None = None
    created_at: dt | None = None

    model_config = ConfigDict(from_attributes=True)


class CreateBudgetLedgerListResponse(BaseModel):
    entries: list[CreateBudgetLedgerEntry]
    total: int


class CreateBudgetSettleRequest(BaseModel):
    settled: bool = True
