from __future__ import annotations

import logging
import random
import time
from datetime import datetime, timezone

from albion_bot.calibration.models import Calibration
from albion_bot.debug_logger import (
    DEBUG_MODE,
    buoc_thanh_cong,
    cap_nhat_buoc,
    tao_bao_cao_loi,
)
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
    backend.click(r.x + r.w // 2, r.y + r.h // 2)
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
        log.debug(f"Tiêu đề cửa sổ Albion: '{title}'")
        # Title format: "Albion Online Client  - <City>"
        if " - " in title:
            city = title.split(" - ", 1)[1].strip() or "Unknown"
            log.debug(f"Thành phố chợ hiện tại: {city}")
            return city
    except Exception as e:
        log.debug(f"Không đọc được tiêu đề cửa sổ: {e}")
    return "Unknown"


def try_sell_item(
    slot: ScannedSlot,
    session_id: str,
    cal: Calibration,
    backend: InputBackend,
    min_sell_price: int,
) -> Transaction | None:
    """
    Thử bán một vật phẩm. Trả về Transaction nếu thành công, None nếu bỏ qua.
    Raise exception nếu gặp lỗi không thể phục hồi.
    """
    regions = cal.regions
    log.debug(f"Bắt đầu thử bán: {slot.full_name} (ô {slot.slot}), giá tối thiểu: {min_sell_price:,}")

    for attempt in range(_MAX_ORDERS_TO_CHECK):
        log.debug(f"Ô {slot.slot}: kiểm tra lệnh mua thứ {attempt + 1}/{_MAX_ORDERS_TO_CHECK}")
        cap_nhat_buoc(
            f"Kiểm tra lệnh mua cho {slot.full_name}",
            o=slot.slot, lan_thu=attempt + 1, gia_toi_thieu=min_sell_price
        )

        # Kiểm tra mất kết nối trước mỗi thao tác
        if is_disconnect_visible(regions.disconnect_icon):
            wait_for_disconnect_clear(cal)

        # Kiểm tra nút bán có màu đỏ không (có lệnh mua phù hợp)
        if not is_red_button(regions.sell_now_button):
            log.info(
                f"Ô {slot.slot}: lệnh mua thứ {attempt + 1} không có nút đỏ — bỏ qua vật phẩm này."
            )
            break

        log.debug(f"Ô {slot.slot}: nút bán màu đỏ — đang đọc giá...")

        # Đọc giá
        price = None
        for doc_lan in range(3):
            price = read_price(regions.buy_order_price)
            if price is not None:
                break
            log.debug(f"Ô {slot.slot}: OCR chưa đọc được giá (lần {doc_lan + 1}/3), chờ {_MARKET_LAG_WAIT}s...")
            time.sleep(_MARKET_LAG_WAIT)

        if price is None:
            log.warning(
                f"Ô {slot.slot}: không đọc được giá sau 3 lần thử — bỏ qua vật phẩm này."
            )
            break

        log.debug(f"Ô {slot.slot}: giá đọc được = {price:,}, tối thiểu = {min_sell_price:,}")

        if price < min_sell_price:
            log.info(
                f"Ô {slot.slot}: giá {price:,} thấp hơn tối thiểu {min_sell_price:,} — bỏ qua."
            )
            return None

        # Nhấn nút bán
        log.debug(f"Ô {slot.slot}: giá hợp lệ — đang nhấn nút bán...")
        cap_nhat_buoc(f"Nhấn nút bán {slot.full_name}", gia=price, o=slot.slot)
        r = regions.sell_now_button
        backend.click(r.x + r.w // 2, r.y + r.h // 2)
        _jitter_sleep(0.4, 0.8)

        # Kiểm tra popup lỗi sau khi bán
        if is_disconnect_visible(regions.disconnect_icon):
            log.warning(f"Ô {slot.slot}: mất kết nối ngay sau khi nhấn bán — hủy giao dịch.")
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
            quantity=1,
            unit_price=price,
            total_price=price,
            market_city=city,
        )
        buoc_thanh_cong(f"Bán {slot.full_name}", gia=price, thanh_pho=city)
        log.info(f"Đã bán: {slot.full_name} @ {price:,} tại {city}")
        return tx

    log.debug(f"Ô {slot.slot}: không tìm được lệnh mua phù hợp sau {_MAX_ORDERS_TO_CHECK} lần kiểm tra.")
    return None
