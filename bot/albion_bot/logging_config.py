import logging
import sys

from albion_bot.debug_logger import DEBUG_MODE, LOG_FILE, setup_file_handler


def setup_logging(level: str = "INFO") -> None:
    # Khi DEBUG=true, tự động hạ xuống mức DEBUG
    if DEBUG_MODE and level.upper() == "INFO":
        level = "DEBUG"

    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    log_level = getattr(logging, level.upper(), logging.INFO)

    handlers: list[logging.Handler] = [
        logging.StreamHandler(sys.stdout),
    ]

    # Luôn ghi log ra file để xem lại sau
    file_handler = setup_file_handler(LOG_FILE)
    handlers.append(file_handler)

    logging.basicConfig(
        level=log_level,
        format=fmt,
        handlers=handlers,
        force=True,
    )

    if DEBUG_MODE:
        logging.getLogger().info(
            f"[DEBUG MODE BẬT] Log chi tiết đang được ghi vào: {LOG_FILE.resolve()}"
        )
    else:
        logging.getLogger().info(
            f"Log đang được ghi vào: {LOG_FILE.resolve()}"
        )

    # Tắt log ồn ào từ thư viện bên thứ ba
    logging.getLogger("ppocr").setLevel(logging.WARNING)
    logging.getLogger("paddle").setLevel(logging.WARNING)
    logging.getLogger("PIL").setLevel(logging.WARNING)
    logging.getLogger("pymongo").setLevel(logging.WARNING)
