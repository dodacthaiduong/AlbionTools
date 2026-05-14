from albion_bot.calibration.models import Rect
from albion_bot.calibration.screen import get_pixel_color


def is_empty_slot(sample_region: Rect, reference_color: tuple[int, int, int], tolerance: int = 15) -> bool:
    """Return True if the pixel at sample_region matches the reference empty-slot color."""
    r, g, b = get_pixel_color(sample_region.x, sample_region.y)
    rr, rg, rb = reference_color
    return (
        abs(r - rr) <= tolerance and
        abs(g - rg) <= tolerance and
        abs(b - rb) <= tolerance
    )


def sample_reference_color(empty_slot_region: Rect) -> tuple[int, int, int]:
    """Read the pixel color from the calibrated empty slot sample region."""
    return get_pixel_color(empty_slot_region.x, empty_slot_region.y)
