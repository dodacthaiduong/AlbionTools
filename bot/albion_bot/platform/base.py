import logging
import sys
import platform as _platform

from albion_bot.debug_logger import buoc_thanh_cong, cap_nhat_buoc

log = logging.getLogger(__name__)


def get_platform() -> str:
    if sys.platform == "win32":
        return "windows"
    if _platform.system() == "Linux":
        return "linux-x11"
    raise RuntimeError(f"Hệ điều hành không được hỗ trợ: {sys.platform}")


class InputBackend:
    def move(self, x: int, y: int) -> None:
        raise NotImplementedError

    def click(self, x: int, y: int) -> None:
        raise NotImplementedError


def get_input_backend() -> InputBackend:
    log.debug("Đang xác định hệ điều hành để chọn bộ điều khiển chuột...")
    cap_nhat_buoc("Khởi tạo bộ điều khiển chuột/bàn phím")
    p = get_platform()
    log.debug(f"Hệ điều hành phát hiện: {p}")
    if p == "linux-x11":
        from albion_bot.platform.linux import LinuxInput
        backend = LinuxInput()
        buoc_thanh_cong("Khởi tạo bộ điều khiển chuột (Linux X11)")
        log.debug("Đã khởi tạo bộ điều khiển chuột cho Linux X11.")
        return backend
    if p == "windows":
        from albion_bot.platform.windows import WindowsInput
        backend = WindowsInput()
        buoc_thanh_cong("Khởi tạo bộ điều khiển chuột (Windows)")
        log.debug("Đã khởi tạo bộ điều khiển chuột cho Windows.")
        return backend
    raise RuntimeError(f"Không có bộ điều khiển chuột cho hệ điều hành: {p}")
