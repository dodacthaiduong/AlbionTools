from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional
from bson import ObjectId
from pydantic import BaseModel, Field


class TransactionItem(BaseModel):
    config_id: Optional[str] = None
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
    status: str = "success"


class SessionStats(BaseModel):
    cycles_completed: int = 0
    items_sold: int = 0
    total_revenue: int = 0
    errors_count: int = 0


class BotSession(BaseModel):
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: Optional[datetime] = None
    status: str = "running"
    stop_reason: Optional[str] = None
    stats: SessionStats = Field(default_factory=SessionStats)
    calibration_id: Optional[str] = None
