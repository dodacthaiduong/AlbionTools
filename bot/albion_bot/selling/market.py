from __future__ import annotations
import time
import random
import logging
from datetime import datetime, timezone

from albion_bot.calibration.models import Calibration
from albion_bot.inventory.models import ScannedSlot
from albion_bot.ocr.reader import read_price, read_text
from albion_bot.platform.base import InputBackend
from albion_bot.selling.detection import is_disconnect_visible, is_red_button
from albion_bot.selling.models import Transaction, TransactionItem

log = logging.getLogger(__name__)

_MARKET_LAG_WAIT = 5.0
_MAX_ORDERS_TO_CHECK = 10


def _jitter_sleep(lo: float = 0.2, hi: float = 0.5) -> None:
    time.sleep(random.uniform(lo, hi))


def wait_for_disconnect_clear(cal: Calibration, poll_interval: float = 2.0) -> None:
    log.warning("Disconnect detected — waiting for reconnect...")
    while is_disconnect_visible(cal.regions.disconnect_icon):
        time.sleep(poll_interval)
    log.info("Reconnected.")
    _jitter_sleep(1.0, 2.0)


def close_popup(backend: InputBackend, cal: Calibration) -> None:
    r = cal.regions.popup_close
    backend.click(r.x + r.w // 2, r.y + r.h // 2)
    _jitter_sleep()


def read_market_city(cal: Calibration) -> str:
    # City name is read from the tooltip_item_name region as a fallback;
    # a dedicated region can be added in a future calibration update.
    return read_text(cal.regions.tooltip_item_name) or "Unknown"


def try_sell_item(
    slot: ScannedSlot,
    session_id: str,
    cal: Calibration,
    backend: InputBackend,
    min_sell_price: int,
) -> Transaction | None:
    """
    Attempt to sell one item. Returns a Transaction on success, None if skipped.
    Raises on unrecoverable error.
    """
    regions = cal.regions

    for attempt in range(_MAX_ORDERS_TO_CHECK):
        # Check disconnect before each interaction
        if is_disconnect_visible(regions.disconnect_icon):
            wait_for_disconnect_clear(cal)

        # Check if sell button is red (order meets item conditions)
        if not is_red_button(regions.sell_now_button):
            log.info(f"Slot {slot.slot}: order {attempt} has black button, skipping order.")
            # Scroll or move to next order — for now we stop checking this item
            # (full order-list navigation is added in M3 polish)
            break

        # Read price
        price = None
        for _ in range(3):
            price = read_price(regions.buy_order_price)
            if price is not None:
                break
            time.sleep(_MARKET_LAG_WAIT)

        if price is None:
            log.warning(f"Slot {slot.slot}: could not read price after retries, skipping.")
            break

        if price < min_sell_price:
            log.info(f"Slot {slot.slot}: price {price} < min {min_sell_price}, skipping.")
            return None

        # Click sell
        r = regions.sell_now_button
        backend.click(r.x + r.w // 2, r.y + r.h // 2)
        _jitter_sleep(0.4, 0.8)

        # Check for error popup
        if is_disconnect_visible(regions.disconnect_icon):
            wait_for_disconnect_clear(cal)
            return None

        city = read_market_city(cal)
        tx = Transaction(
            session_id=session_id,
            item=TransactionItem(
                full_name=slot.full_name,
                tier=slot.tier,
                enchant=slot.enchant,
            ),
            quantity=1,  # actual quantity filled from sell dialog in future polish
            unit_price=price,
            total_price=price,
            market_city=city,
        )
        log.info(f"Sold {slot.full_name} @ {price} in {city}")
        return tx

    return None
