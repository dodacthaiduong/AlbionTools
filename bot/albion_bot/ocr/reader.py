from __future__ import annotations
import re
from functools import lru_cache

import numpy as np
from paddleocr import PaddleOCR

from albion_bot.calibration.models import Rect
from albion_bot.calibration.screen import capture_region


@lru_cache(maxsize=1)
def _get_ocr() -> PaddleOCR:
    return PaddleOCR(use_angle_cls=False, lang="en", show_log=False)


def _region_to_array(region: Rect) -> np.ndarray:
    import io
    from PIL import Image
    png = capture_region(region)
    img = Image.open(io.BytesIO(png)).convert("RGB")
    return np.array(img)


def read_text(region: Rect) -> str:
    ocr = _get_ocr()
    arr = _region_to_array(region)
    result = ocr.ocr(arr, cls=False)
    if not result or not result[0]:
        return ""
    lines = [line[1][0] for line in result[0] if line and line[1]]
    return " ".join(lines).strip()


def read_price(region: Rect) -> int | None:
    raw = read_text(region)
    digits = re.sub(r"[^\d]", "", raw)
    return int(digits) if digits else None


# Albion item names follow: "Tier's Adjective Noun" or "Adept's Leather Bag"
# Tier words map to numeric tiers
_TIER_WORDS = {
    "novice": 2, "journeyman": 3, "adept": 4, "expert": 5,
    "master": 6, "grandmaster": 7, "elder": 8,
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
        raw = raw[:m.start()].strip()

    tier = 1
    lower = raw.lower()
    for word, t in _TIER_WORDS.items():
        if lower.startswith(word):
            tier = t
            break

    return raw, tier, enchant
