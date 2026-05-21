import random

import pydirectinput

from albion_bot.platform.base import InputBackend


class WindowsInput(InputBackend):
    def move(self, x: int, y: int) -> None:
        jx = x + random.randint(-3, 3)
        jy = y + random.randint(-3, 3)
        pydirectinput.moveTo(jx, jy)

    def click(self, x: int, y: int) -> None:
        self.move(x, y)
        pydirectinput.click(x, y)

    def type_text(self, text: str) -> None:
        pydirectinput.write(text, interval=0.02)

    def hotkey(self, *keys: str) -> None:
        if not keys:
            return
        pydirectinput.hotkey(*keys)
