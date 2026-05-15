import logging

from pymongo import MongoClient
from pymongo.database import Database

from albion_bot.debug_logger import buoc_thanh_cong, cap_nhat_buoc

log = logging.getLogger(__name__)

_client: MongoClient | None = None


def get_db(uri: str = "mongodb://localhost:27017", db_name: str = "albion_bot") -> Database:
    global _client
    if _client is None:
        log.debug(f"Đang kết nối MongoDB tại {uri}...")
        cap_nhat_buoc("Kết nối MongoDB", uri=uri, db=db_name)
        try:
            _client = MongoClient(uri, serverSelectionTimeoutMS=5000)
            # Kiểm tra kết nối thực sự
            _client.admin.command("ping")
            buoc_thanh_cong("Kết nối MongoDB", uri=uri)
            log.debug(f"Đã kết nối MongoDB thành công. Database: '{db_name}'")
        except Exception as e:
            log.error(f"Không thể kết nối MongoDB tại {uri}: {e}")
            log.error("Nguyên nhân có thể: MongoDB chưa chạy, sai địa chỉ, hoặc firewall chặn cổng 27017.")
            _client = None
            raise
    return _client[db_name]


def close():
    global _client
    if _client is not None:
        log.debug("Đang đóng kết nối MongoDB...")
        _client.close()
        _client = None
        log.debug("Đã đóng kết nối MongoDB.")
