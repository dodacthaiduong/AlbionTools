from __future__ import annotations

import json
import logging
import math
from typing import Optional
from urllib.error import URLError
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

from albion_bot.inventory.models import ScannedSlot
from albion_bot.ocr.reader import read_price

log = logging.getLogger(__name__)

LISTING_FEE_RATE = 0.025
TRANSACTION_FEE_RATE_PREMIUM = 0.04
TRANSACTION_FEE_RATE_NON_PREMIUM = 0.08
PRICE_STEP = 1000


class PriceDecision(dict):
    """Simple typed mapping for pricing decision details."""


def calc_target_sell_order_price(lowest_sell_price: int) -> Optional[int]:
    """Apply the requested rounding rule.

    Examples:
    - 191900 -> 191000
    - 191000 -> 190000
    """
    if lowest_sell_price <= 0:
        return None

    rounded_down = (lowest_sell_price // PRICE_STEP) * PRICE_STEP
    if lowest_sell_price % PRICE_STEP == 0:
        target = rounded_down - PRICE_STEP
    else:
        target = rounded_down

    if target <= 0:
        return None
    return target


def _calc_fees(price: int, is_premium: bool) -> tuple[int, int, int]:
    tx_rate = TRANSACTION_FEE_RATE_PREMIUM if is_premium else TRANSACTION_FEE_RATE_NON_PREMIUM
    listing_fee = int(math.ceil(price * LISTING_FEE_RATE))
    transaction_fee = int(math.ceil(price * tx_rate))
    net_revenue = price - listing_fee - transaction_fee
    return listing_fee, transaction_fee, net_revenue


def evaluate_sell_order_price(
    lowest_sell_price: int,
    cost_price: int,
    is_premium: bool,
) -> Optional[PriceDecision]:
    target = calc_target_sell_order_price(lowest_sell_price)
    if target is None:
        return None

    listing_fee, transaction_fee, net_revenue = _calc_fees(target, is_premium)
    if net_revenue < cost_price:
        return None

    return PriceDecision(
        listed_price=target,
        listing_fee=listing_fee,
        transaction_fee=transaction_fee,
        net_revenue=net_revenue,
    )


def get_lowest_sell_price_ocr(region) -> Optional[int]:
    """Read lowest sell order price from calibrated region."""
    return read_price(region)


def _api_get_json(url: str, timeout: float = 3.5):
    req = Request(url, headers={"User-Agent": "albion-auto-seller/1.0"})
    with urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
        return json.loads(raw)


def _find_item_id(slot: ScannedSlot) -> Optional[str]:
    """Best-effort lookup of Albion Data item id via search endpoint."""
    query = quote_plus(f"T{slot.tier} {slot.base_name}")
    url = f"https://west.albion-online-data.com/api/v2/search?q={query}"

    try:
        data = _api_get_json(url)
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        log.debug("API search failed for '%s': %s", slot.full_name, exc)
        return None
    except Exception as exc:
        log.debug("Unexpected API search failure for '%s': %s", slot.full_name, exc)
        return None

    expected_tier = f"T{slot.tier}"
    expected_enchant = f"@{slot.enchant}" if slot.enchant > 0 else None

    # Pass 1: strict by name + tier + enchant
    for row in data if isinstance(data, list) else []:
        item_id = str(row.get("Id", ""))
        item_name = str(row.get("Name", ""))
        if not item_id.startswith(expected_tier):
            continue
        if slot.base_name.lower() not in item_name.lower():
            continue
        if expected_enchant is not None and expected_enchant not in item_id:
            continue
        if expected_enchant is None and "@" in item_id:
            continue
        return item_id

    # Pass 2: relaxed by tier (+ enchant if present)
    for row in data if isinstance(data, list) else []:
        item_id = str(row.get("Id", ""))
        if not item_id.startswith(expected_tier):
            continue
        if expected_enchant is not None and expected_enchant not in item_id:
            continue
        if expected_enchant is None and "@" in item_id:
            continue
        return item_id

    return None


def get_lowest_sell_price_api(slot: ScannedSlot, market_city: str) -> Optional[int]:
    item_id = _find_item_id(slot)
    if not item_id:
        return None

    location = quote_plus(market_city or "")
    url = (
        "https://west.albion-online-data.com/api/v2/stats/prices/"
        f"{item_id}.json?locations={location}&qualities=1"
    )

    try:
        data = _api_get_json(url)
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        log.debug("API price failed for item '%s': %s", item_id, exc)
        return None
    except Exception as exc:
        log.debug("Unexpected API price failure for '%s': %s", item_id, exc)
        return None

    prices: list[int] = []
    for row in data if isinstance(data, list) else []:
        p = row.get("sell_price_min")
        if isinstance(p, int) and p > 0:
            prices.append(p)

    if not prices:
        return None
    return min(prices)


def get_lowest_sell_price(slot: ScannedSlot, market_city: str, ocr_region) -> Optional[int]:
    """OCR first, API fallback."""
    ocr_price = get_lowest_sell_price_ocr(ocr_region)
    if ocr_price is not None and ocr_price > 0:
        return ocr_price

    api_price = get_lowest_sell_price_api(slot, market_city)
    if api_price is not None and api_price > 0:
        return api_price

    return None
