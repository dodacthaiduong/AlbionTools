from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field


class ItemConfig(BaseModel):
    item_id: Optional[str] = None
    base_name: str
    full_name: str
    tier: int
    enchant: int
    estimated_price: Optional[int] = None
    min_sell_price: Optional[int] = None
    enabled: bool = True
    last_scanned_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ScannedSlot(BaseModel):
    slot: int
    full_name: str
    base_name: str
    tier: int
    enchant: int
    quantity: int
    estimated_price: Optional[int] = None
    empty: bool = False
