import sys
import platform as _platform


def get_platform() -> str:
    if sys.platform == "win32":
        return "windows"
    if _platform.system() == "Linux":
        return "linux-x11"
    raise RuntimeError(f"Unsupported platform: {sys.platform}")


class InputBackend:
    def move(self, x: int, y: int) -> None:
        raise NotImplementedError

    def click(self, x: int, y: int) -> None:
        raise NotImplementedError


def get_input_backend() -> InputBackend:
    p = get_platform()
    if p == "linux-x11":
        from albion_bot.platform.linux import LinuxInput
        return LinuxInput()
    if p == "windows":
        from albion_bot.platform.windows import WindowsInput
        return WindowsInput()
    raise RuntimeError(f"No input backend for {p}")
