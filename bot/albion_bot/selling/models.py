from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class TransactionItem(BaseModel):
    config_id: Optional[str] = None
    base_name: Optional[str] = None
    full_name: str
    tier: int
    enchant: int


class Transaction(BaseModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    session_id: str
    item: TransactionItem
    quantity: int
    unit_price: int
    total_price: int
    market_city: str
    status: str = "filled"

    # Extended accounting for sell-order flow
    order_type: str = "sell_order"
    listing_fee: int = 0
    transaction_fee: int = 0
    net_revenue: int = 0
    related_order_id: Optional[str] = None


class SellOrder(BaseModel):
    listed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    filled_at: Optional[datetime] = None
    session_id: str
    item: TransactionItem
    quantity: int = 1
    listed_price: int
    market_city: str
    is_premium: bool
    listing_fee: int
    transaction_fee_est: int
    net_revenue_est: int
    status: str = "open"  # open | filled | cancelled


class SessionStats(BaseModel):
    cycles_completed: int = 0
    items_sold: int = 0
    total_revenue: int = 0
    errors_count: int = 0

    # New metrics for sell-order loop
    orders_placed: int = 0
    orders_filled: int = 0


class BotSession(BaseModel):
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: Optional[datetime] = None
    status: str = "running"
    stop_reason: Optional[str] = None
    stats: SessionStats = Field(default_factory=SessionStats)
    calibration_id: Optional[str] = None
