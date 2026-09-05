from datetime import datetime as dt
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


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
    group_ids: list[int] = Field(default_factory=list)
    ip_limit: int | None = Field(default=None, ge=0)
    hwid_limit: int | None = Field(default=None, ge=0)
    is_active: bool = True


class ShopPlanUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=64)
    data_limit: int | None = Field(default=None, ge=0)
    expire_days: int | None = Field(default=None, ge=0)
    price_toman: int | None = Field(default=None, ge=0)
    group_ids: list[int] | None = None
    ip_limit: int | None = Field(default=None, ge=0)
    hwid_limit: int | None = Field(default=None, ge=0)
    is_active: bool | None = None


class ShopOrderResponse(BaseModel):
    id: int
    plan_id: int
    admin_id: int
    buyer_telegram_id: int
    buyer_username: str | None = None
    status: ShopOrderStatusLiteral
    receipt_file_id: str | None = None
    created_user_id: int | None = None
    created_username: str | None = None
    plan_name: str | None = None
    plan_price_toman: int | None = None
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


class ShopApproveResponse(BaseModel):
    order: ShopOrderResponse
    username: str
    subscription_url: str | None = None
