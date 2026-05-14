import random
import time
from Xlib import display, X
from Xlib.ext.xtest import fake_input
from albion_bot.platform.base import InputBackend


class LinuxInput(InputBackend):
    def __init__(self):
        self._display = display.Display()

    def move(self, x: int, y: int) -> None:
        jx = x + random.randint(-3, 3)
        jy = y + random.randint(-3, 3)
        fake_input(self._display, X.MotionNotify, x=jx, y=jy)
        self._display.sync()

    def click(self, x: int, y: int) -> None:
        self.move(x, y)
        time.sleep(random.uniform(0.05, 0.12))
        fake_input(self._display, X.ButtonPress, detail=1)
        self._display.sync()
        time.sleep(random.uniform(0.05, 0.10))
        fake_input(self._display, X.ButtonRelease, detail=1)
        self._display.sync()
