from __future__ import annotations

import logging
import random
import time
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId

from albion_bot.calibration.models import Calibration, Rect
from albion_bot.db.connection import get_db
from albion_bot.debug_logger import buoc_thanh_cong, cap_nhat_buoc
from albion_bot.inventory.models import ScannedSlot
from albion_bot.ocr.reader import read_text
from albion_bot.platform.base import InputBackend
from albion_bot.selling.detection import is_disconnect_visible
from albion_bot.selling.models import SellOrder, Transaction, TransactionItem
from albion_bot.selling.price import evaluate_sell_order_price, get_lowest_sell_price

log = logging.getLogger(__name__)


def _jitter_sleep(lo: float = 0.2, hi: float = 0.5) -> None:
    time.sleep(random.uniform(lo, hi))


def _require_region(region: Optional[Rect], key: str) -> Rect:
    if region is None:
        raise RuntimeError(
            f"Calibration region '{key}' chưa được chọn. Hãy mở tab Calibration và chọn lại vùng này."
        )
    return region


def _center_click(backend: InputBackend, rect: Rect) -> None:
    backend.click(rect.x + rect.w // 2, rect.y + rect.h // 2)


def wait_for_disconnect_clear(cal: Calibration, poll_interval: float = 2.0) -> None:
    log.warning("Phát hiện mất kết nối — đang chờ kết nối lại...")
    cap_nhat_buoc("Chờ kết nối lại")
    while is_disconnect_visible(cal.regions.disconnect_icon):
        time.sleep(poll_interval)
    log.info("Đã kết nối lại thành công.")
    buoc_thanh_cong("Kết nối lại")
    _jitter_sleep(1.0, 2.0)


def close_popup(backend: InputBackend, cal: Calibration) -> None:
    log.debug("Đang đóng cửa sổ popup...")
    r = cal.regions.popup_close
    _center_click(backend, r)
    _jitter_sleep()


def read_market_city(cal: Calibration) -> str:
    """Đọc tên thành phố chợ từ tiêu đề cửa sổ qua xdotool."""
    try:
        import subprocess

        result = subprocess.run(
            ["xdotool", "getactivewindow", "getwindowname"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        title = result.stdout.strip()
        # Title format: "Albion Online Client  - <City>"
        if " - " in title:
            city = title.split(" - ", 1)[1].strip() or "Unknown"
            return city
    except Exception as e:
        log.debug(f"Không đọc được tiêu đề cửa sổ: {e}")
    return "Unknown"


def _item_order_filter(slot: ScannedSlot) -> dict:
    return {
        "item.base_name": slot.base_name,
        "item.tier": slot.tier,
        "item.enchant": slot.enchant,
        "status": "open",
    }


def has_open_sell_order(slot: ScannedSlot) -> bool:
    db = get_db()
    return db.sell_orders.find_one(_item_order_filter(slot)) is not None


def place_sell_order(
    slot: ScannedSlot,
    session_id: str,
    cal: Calibration,
    backend: InputBackend,
    cost_price: int,
    is_premium: bool,
) -> SellOrder | None:
    """Place a sell order for one item slot.

    Returns SellOrder if successfully listed, None if skipped by price/profit checks.
    Raises exception for non-recoverable workflow errors.
    """
    regions = cal.regions

    # Avoid duplicate open orders for the same item type.
    if has_open_sell_order(slot):
        log.debug(
            "Đã có open order cho %s (T%s.%s) — bỏ qua.",
            slot.base_name,
            slot.tier,
            slot.enchant,
        )
        return None

    if is_disconnect_visible(regions.disconnect_icon):
        wait_for_disconnect_clear(cal)

    sell_order_price_input = _require_region(regions.sell_order_price_input, "sell_order_price_input")
    sell_order_confirm_button = _require_region(
        regions.sell_order_confirm_button,
        "sell_order_confirm_button",
    )

    market_city = read_market_city(cal)
    lowest_price = get_lowest_sell_price(slot, market_city, regions.lowest_sell_order_price)
    if lowest_price is None:
        log.info(
            "Ô %s (%s): không đọc được giá sell order thấp nhất (OCR/API đều fail) — bỏ qua.",
            slot.slot,
            slot.full_name,
        )
        return None

    decision = evaluate_sell_order_price(lowest_price, cost_price, is_premium)
    if decision is None:
        log.info(
            "Ô %s (%s): đặt order không đạt điều kiện lợi nhuận sau phí (lowest=%s, cost=%s) — bỏ qua.",
            slot.slot,
            slot.full_name,
            lowest_price,
            cost_price,
        )
        return None

    listed_price = int(decision["listed_price"])
    listing_fee = int(decision["listing_fee"])
    transaction_fee = int(decision["transaction_fee"])
    net_revenue = int(decision["net_revenue"])

    cap_nhat_buoc(
        f"Đặt sell order {slot.full_name}",
        o=slot.slot,
        gia_thap_nhat=lowest_price,
        gia_dat=listed_price,
        gia_von=cost_price,
    )

    # Select item slot again (safety), then fill sell-order input.
    # scan_inventory already clicked slots earlier; we click center point once more for reliability.
    # Here we assume current UI focus is still in market/inventory context.
    _center_click(backend, sell_order_price_input)
    _jitter_sleep(0.1, 0.2)
    backend.hotkey("ctrl", "a")
    _jitter_sleep(0.05, 0.15)
    backend.type_text(str(listed_price))
    _jitter_sleep(0.15, 0.3)

    if is_disconnect_visible(regions.disconnect_icon):
        wait_for_disconnect_clear(cal)
        return None

    _center_click(backend, sell_order_confirm_button)
    _jitter_sleep(0.4, 0.8)

    order = SellOrder(
        session_id=session_id,
        item=TransactionItem(
            base_name=slot.base_name,
            full_name=slot.full_name,
            tier=slot.tier,
            enchant=slot.enchant,
        ),
        quantity=1,
        listed_price=listed_price,
        market_city=market_city,
        is_premium=is_premium,
        listing_fee=listing_fee,
        transaction_fee_est=transaction_fee,
        net_revenue_est=net_revenue,
        status="open",
    )

    db = get_db()
    db.sell_orders.insert_one(order.model_dump())

    buoc_thanh_cong(
        f"Đặt sell order {slot.full_name}",
        gia_dat=listed_price,
        listing_fee=listing_fee,
        transaction_fee=transaction_fee,
        net=net_revenue,
    )
    log.info(
        "Đã đặt sell order: %s @ %s (%s) | net est=%s",
        slot.full_name,
        f"{listed_price:,}",
        market_city,
        f"{net_revenue:,}",
    )
    return order


def _normalize(s: str) -> str:
    return " ".join((s or "").lower().split())


def _is_order_still_visible(order: dict, ocr_text: str) -> bool:
    item = order.get("item", {})
    full_name = _normalize(str(item.get("full_name", "")))
    base_name = _normalize(str(item.get("base_name", "")))
    text = _normalize(ocr_text)

    if full_name and full_name in text:
        return True
    if base_name and base_name in text:
        return True
    return False


def reconcile_filled_orders(cal: Calibration, backend: InputBackend) -> list[Transaction]:
    """Poll My Orders and mark missing open orders as filled.

    Returns transactions generated from newly-filled orders.
    """
    regions = cal.regions
    my_orders_tab = _require_region(regions.my_orders_tab, "my_orders_tab")
    my_orders_list = _require_region(regions.my_orders_list, "my_orders_list")

    if is_disconnect_visible(regions.disconnect_icon):
        wait_for_disconnect_clear(cal)

    _center_click(backend, my_orders_tab)
    _jitter_sleep(0.25, 0.45)

    open_text = read_text(my_orders_list)
    if not open_text.strip():
        log.warning(
            "Không OCR được nội dung My Orders — bỏ qua reconcile chu kỳ này để tránh false positive."
        )
        return []

    db = get_db()
    open_orders = list(db.sell_orders.find({"status": "open"}).sort("listed_at", 1))
    if not open_orders:
        return []

    now = datetime.now(timezone.utc)
    filled_txs: list[Transaction] = []
    for order in open_orders:
        if _is_order_still_visible(order, open_text):
            continue

        order_id = order.get("_id")
        db.sell_orders.update_one(
            {"_id": order_id},
            {"$set": {"status": "filled", "filled_at": now}},
        )

        item = order.get("item", {})
        listed_price = int(order.get("listed_price", 0) or 0)
        listing_fee = int(order.get("listing_fee", 0) or 0)
        transaction_fee = int(order.get("transaction_fee_est", 0) or 0)
        net_revenue = int(order.get("net_revenue_est", 0) or 0)

        tx = Transaction(
            session_id=str(order.get("session_id", "")),
            item=TransactionItem(
                base_name=item.get("base_name"),
                full_name=str(item.get("full_name", "Unknown")),
                tier=int(item.get("tier", 0) or 0),
                enchant=int(item.get("enchant", 0) or 0),
            ),
            quantity=int(order.get("quantity", 1) or 1),
            unit_price=listed_price,
            total_price=listed_price,
            market_city=str(order.get("market_city", "Unknown")),
            status="filled",
            order_type="sell_order",
            listing_fee=listing_fee,
            transaction_fee=transaction_fee,
            net_revenue=net_revenue,
            related_order_id=str(order_id) if isinstance(order_id, ObjectId) else None,
        )
        filled_txs.append(tx)

    return filled_txs
