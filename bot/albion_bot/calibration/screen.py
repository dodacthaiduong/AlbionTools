import mss
import mss.tools
from albion_bot.calibration.models import Rect


def get_screen_size() -> dict[str, int]:
    with mss.mss() as sct:
        m = sct.monitors[1]
        return {"width": m["width"], "height": m["height"]}


def capture_region(region: Rect) -> bytes:
    with mss.mss() as sct:
        mon = {"left": region.x, "top": region.y, "width": region.w, "height": region.h}
        img = sct.grab(mon)
        return mss.tools.to_png(img.rgb, img.size)


def get_pixel_color(x: int, y: int) -> tuple[int, int, int]:
    with mss.mss() as sct:
        mon = {"left": x, "top": y, "width": 1, "height": 1}
        img = sct.grab(mon)
        r, g, b = img.rgb[0], img.rgb[1], img.rgb[2]
        return (r, g, b)
