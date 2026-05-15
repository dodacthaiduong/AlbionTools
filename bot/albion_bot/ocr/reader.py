from __future__ import annotations

import logging
import re
from functools import lru_cache

import numpy as np
from paddleocr import PaddleOCR

from albion_bot.calibration.models import Rect
from albion_bot.calibration.screen import capture_region
from albion_bot.debug_logger import DEBUG_MODE, cap_nhat_buoc

log = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_ocr() -> PaddleOCR:
    log.debug("Đang khởi tạo engine OCR (PaddleOCR)... lần đầu sẽ mất vài giây.")
    ocr = PaddleOCR(use_angle_cls=False, lang="en", show_log=False)
    log.debug("Engine OCR đã sẵn sàng.")
    return ocr


def _region_to_array(region: Rect) -> np.ndarray:
    import io

    from PIL import Image

    log.debug(f"Đang chụp vùng màn hình: x={region.x}, y={region.y}, w={region.w}, h={region.h}")
    png = capture_region(region)
    img = Image.open(io.BytesIO(png)).convert("RGB")
    return np.array(img)


def read_text(region: Rect) -> str:
    cap_nhat_buoc("Đọc chữ từ màn hình (OCR)", vung=f"{region.x},{region.y},{region.w},{region.h}")
    try:
        ocr = _get_ocr()
        arr = _region_to_array(region)
        result = ocr.ocr(arr, cls=False)
        if not result or not result[0]:
            log.debug("OCR không nhận ra chữ nào trong vùng này.")
            return ""
        lines = [line[1][0] for line in result[0] if line and line[1]]
        text = " ".join(lines).strip()
        log.debug(f"OCR đọc được: '{text}'")
        return text
    except Exception as e:
        log.warning(f"Lỗi khi đọc chữ OCR: {e}")
        return ""


def read_price(region: Rect) -> int | None:
    log.debug("Đang đọc giá từ màn hình...")
    raw = read_text(region)
    digits = re.sub(r"[^\d]", "", raw)
    if not digits:
        log.debug(f"Không tìm thấy số trong chuỗi OCR: '{raw}'")
        return None
    price = int(digits)
    log.debug(f"Giá đọc được: {price:,} (từ chuỗi gốc: '{raw}')")
    return price


# Albion item names follow: "Tier's Adjective Noun" or "Adept's Leather Bag"
# Tier words map to numeric tiers
_TIER_WORDS = {
    "novice": 2,
    "journeyman": 3,
    "adept": 4,
    "expert": 5,
    "master": 6,
    "grandmaster": 7,
    "elder": 8,
}

# Enchant suffix: @1, @2, @3, @4 appended by some OCR reads, or ".1" etc.
_ENCHANT_RE = re.compile(r"[.@]([1-4])$", re.IGNORECASE)


def parse_item_name(raw: str) -> tuple[str, int, int]:
    """Return (base_name, tier, enchant) from a raw OCR item name string."""
    raw = raw.strip()
    enchant = 0
    m = _ENCHANT_RE.search(raw)
    if m:
        enchant = int(m.group(1))
        raw = raw[: m.start()].strip()

    tier = 1
    lower = raw.lower()
    for word, t in _TIER_WORDS.items():
        if lower.startswith(word):
            tier = t
            # Strip the tier word and possessive suffix (e.g. "Adept's ")
            raw = raw[len(word) :].lstrip("' ").strip()
            break

    return raw, tier, enchant
