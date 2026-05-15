import logging
import random
import time
from Xlib import display, X
from Xlib.ext.xtest import fake_input
from albion_bot.platform.base import InputBackend

log = logging.getLogger(__name__)


class LinuxInput(InputBackend):
    def __init__(self):
        log.debug("Đang kết nối với X11 display...")
        try:
            self._display = display.Display()
            log.debug("Đã kết nối X11 display thành công.")
        except Exception as e:
            log.error(f"Không thể kết nối X11 display: {e}")
            log.error("Nguyên nhân có thể: biến môi trường DISPLAY chưa được đặt, hoặc không chạy trong môi trường đồ họa.")
            raise

    def move(self, x: int, y: int) -> None:
        jx = x + random.randint(-3, 3)
        jy = y + random.randint(-3, 3)
        log.debug(f"Di chuyển chuột đến ({jx}, {jy}) [mục tiêu: ({x}, {y})]")
        fake_input(self._display, X.MotionNotify, x=jx, y=jy)
        self._display.sync()

    def click(self, x: int, y: int) -> None:
        self.move(x, y)
        time.sleep(random.uniform(0.05, 0.12))
        log.debug(f"Nhấn chuột trái tại ({x}, {y})")
        fake_input(self._display, X.ButtonPress, detail=1)
        self._display.sync()
        time.sleep(random.uniform(0.05, 0.10))
        fake_input(self._display, X.ButtonRelease, detail=1)
        self._display.sync()
