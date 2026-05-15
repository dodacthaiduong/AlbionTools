"""
Module debug/logging trung tâm cho Albion Bot.

Cách dùng:
  - Đặt biến môi trường DEBUG=true để bật chế độ debug chi tiết
  - Log được lưu vào file debug.log trong thư mục chạy bot
  - Khi có lỗi, gọi tao_bao_cao_loi() để tạo khối báo cáo sẵn để copy
"""
from __future__ import annotations

import logging
import os
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ── Cấu hình DEBUG mode ──────────────────────────────────────────────────────
DEBUG_MODE: bool = os.environ.get("DEBUG", "false").lower() in ("true", "1", "yes")

# ── Đường dẫn file log ───────────────────────────────────────────────────────
LOG_FILE = Path(os.environ.get("LOG_FILE", "debug.log"))

# ── Trạng thái bước hiện tại (dùng để báo cáo lỗi) ──────────────────────────
_buoc_thanh_cong_cuoi: str = "Chưa bắt đầu"
_buoc_hien_tai: str = "Chưa bắt đầu"
_thong_tin_lien_quan: dict[str, Any] = {}


def cap_nhat_buoc(ten_buoc: str, **thong_tin: Any) -> None:
    """Ghi nhận bước đang thực hiện để dùng khi báo cáo lỗi."""
    global _buoc_thanh_cong_cuoi, _buoc_hien_tai, _thong_tin_lien_quan
    _buoc_thanh_cong_cuoi = _buoc_hien_tai
    _buoc_hien_tai = ten_buoc
    _thong_tin_lien_quan = thong_tin


def buoc_thanh_cong(ten_buoc: str, **thong_tin: Any) -> None:
    """Đánh dấu bước vừa hoàn thành thành công."""
    global _buoc_thanh_cong_cuoi, _buoc_hien_tai, _thong_tin_lien_quan
    _buoc_thanh_cong_cuoi = ten_buoc
    _buoc_hien_tai = ten_buoc
    _thong_tin_lien_quan = thong_tin


def tao_bao_cao_loi(loi: Exception | str, module: str = "") -> str:
    """
    Tạo khối báo cáo lỗi được format sẵn.
    Người dùng chỉ cần copy toàn bộ khối này để báo cáo.
    """
    thoi_gian = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    noi_dung_loi = traceback.format_exc() if isinstance(loi, Exception) else str(loi)

    dong_phan_cach = "=" * 60
    bao_cao = f"""
{dong_phan_cach}
🔴 BÁO CÁO LỖI ALBION BOT
{dong_phan_cach}
📅 Thời gian xảy ra  : {thoi_gian}
📍 Module            : {module or 'Không rõ'}
✅ Bước cuối thành công: {_buoc_thanh_cong_cuoi}
❌ Bước bị lỗi       : {_buoc_hien_tai}

📋 Nội dung lỗi:
{str(loi)}

🔍 Chi tiết kỹ thuật:
{noi_dung_loi}"""

    if _thong_tin_lien_quan:
        bao_cao += "\n📦 Thông tin liên quan:"
        for k, v in _thong_tin_lien_quan.items():
            bao_cao += f"\n   {k}: {v}"

    bao_cao += f"\n{dong_phan_cach}\n"
    return bao_cao


def setup_file_handler(log_file: Path | None = None) -> logging.FileHandler:
    """Tạo handler ghi log ra file."""
    path = log_file or LOG_FILE
    handler = logging.FileHandler(path, encoding="utf-8")
    handler.setLevel(logging.DEBUG)
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(fmt)
    return handler


def get_debug_logger(name: str) -> logging.Logger:
    """Lấy logger đã được cấu hình cho module."""
    return logging.getLogger(name)
