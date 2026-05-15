from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class Rect(BaseModel):
    x: int
    y: int
    w: int
    h: int


class Point(BaseModel):
    x: int
    y: int


class Cell(BaseModel):
    index: int
    x: int
    y: int


class InventoryConfig(BaseModel):
    rows: int = 8
    cols: int = 6
    grid_rect: Rect  # bounding box of the entire inventory grid
    cells: list[Cell] = Field(default_factory=list)


class Regions(BaseModel):
    sell_now_button: Rect
    buy_order_price: Rect
    tooltip_item_name: Rect
    tooltip_est_price: Rect
    disconnect_icon: Rect
    popup_close: Rect
    sort_button: Rect
    stack_button: Rect
    empty_slot_sample: Rect


class Calibration(BaseModel):
    profile_name: str = "default"
    platform: str
    screen: dict[str, int]
    inventory: InventoryConfig
    regions: Regions
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
