from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field, model_validator


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
    lowest_sell_order_price: Rect
    tooltip_item_name: Rect
    tooltip_est_price: Rect
    disconnect_icon: Rect
    popup_close: Rect
    sort_button: Rect
    stack_button: Rect
    empty_slot_sample: Rect

    # New regions for sell-order workflow
    sell_order_price_input: Optional[Rect] = None
    sell_order_confirm_button: Optional[Rect] = None
    my_orders_tab: Optional[Rect] = None
    my_orders_list: Optional[Rect] = None

    @model_validator(mode="before")
    @classmethod
    def _legacy_buy_order_price_alias(cls, data):
        if isinstance(data, dict):
            if "lowest_sell_order_price" not in data and "buy_order_price" in data:
                data["lowest_sell_order_price"] = data["buy_order_price"]
        return data


class Calibration(BaseModel):
    profile_name: str = "default"
    platform: str
    screen: dict[str, int]
    inventory: InventoryConfig
    regions: Regions
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
