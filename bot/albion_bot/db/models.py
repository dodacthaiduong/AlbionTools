from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field


class Item(BaseModel):
    name: str
    category1: Optional[str] = None
    category2: Optional[str] = None
    category3: Optional[str] = None
    tier: int
    enchantment: int
    quality: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
