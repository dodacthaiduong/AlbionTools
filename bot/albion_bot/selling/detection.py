from albion_bot.calibration.models import Rect
from albion_bot.calibration.screen import get_pixel_color


# Red sell button: high red, low green, low blue
_RED_MIN = (150, 0, 0)
_RED_MAX = (255, 80, 80)

# Tolerance for color matching
_TOLERANCE = 30


def _in_range(val: int, lo: int, hi: int) -> bool:
    return lo - _TOLERANCE <= val <= hi + _TOLERANCE


def is_red_button(region: Rect) -> bool:
    """Sample the center of the sell button region; return True if it's red (sellable)."""
    cx = region.x + region.w // 2
    cy = region.y + region.h // 2
    r, g, b = get_pixel_color(cx, cy)
    return (
        _in_range(r, _RED_MIN[0], _RED_MAX[0]) and
        _in_range(g, _RED_MIN[1], _RED_MAX[1]) and
        _in_range(b, _RED_MIN[2], _RED_MAX[2])
    )


def is_disconnect_visible(region: Rect) -> bool:
    """Detect disconnect icon by checking for a non-background pixel in the region."""
    r, g, b = get_pixel_color(region.x + region.w // 2, region.y + region.h // 2)
    # Disconnect icon is typically bright/orange — not pure black background
    return (r + g + b) > 60
