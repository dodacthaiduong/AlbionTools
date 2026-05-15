from __future__ import annotations

import json
import logging
from pathlib import Path

from albion_bot.calibration.models import Calibration, Cell, Rect
from albion_bot.db.connection import get_db
from albion_bot.debug_logger import buoc_thanh_cong, cap_nhat_buoc, tao_bao_cao_loi

log = logging.getLogger(__name__)


def _compute_cells(grid_rect: Rect, rows: int, cols: int) -> list[Cell]:
    """Chia grid_rect thành lưới rows×cols và trả về tâm mỗi ô."""
    log.debug(f"Đang tính toán {rows}x{cols} = {rows*cols} ô trong lưới kho đồ...")
    cell_w = grid_rect.w / cols
    cell_h = grid_rect.h / rows

    cells: list[Cell] = []
    for i in range(rows * cols):
        row = i // cols
        col = i % cols
        cells.append(
            Cell(
                index=i,
                x=round(grid_rect.x + col * cell_w + cell_w / 2),
                y=round(grid_rect.y + row * cell_h + cell_h / 2),
            )
        )
    log.debug(f"Đã tính xong {len(cells)} ô.")
    return cells


def save_calibration(cal: Calibration, backup_dir: str = ".") -> str:
    """Lưu calibration vào MongoDB và tạo file JSON backup.

    Trả về chuỗi _id của document MongoDB.
    """
    log.info(f"Đang lưu calibration cho profile '{cal.profile_name}'...")
    cap_nhat_buoc("Lưu calibration", profile=cal.profile_name)

    # Luôn tính lại các ô để đảm bảo nhất quán
    log.debug("Đang tính lại vị trí các ô kho đồ...")
    cal.inventory.cells = _compute_cells(
        cal.inventory.grid_rect,
        cal.inventory.rows,
        cal.inventory.cols,
    )

    try:
        db = get_db()
        doc = cal.model_dump()

        existing = db.calibrations.find_one({"profile_name": cal.profile_name})
        if existing:
            log.debug(f"Profile '{cal.profile_name}' đã tồn tại — đang cập nhật...")
            db.calibrations.replace_one({"_id": existing["_id"]}, doc)
            inserted_id = str(existing["_id"])
            log.info(f"Đã cập nhật calibration profile '{cal.profile_name}' (ID: {inserted_id})")
        else:
            log.debug(f"Profile '{cal.profile_name}' chưa có — đang tạo mới...")
            result = db.calibrations.insert_one(doc)
            inserted_id = str(result.inserted_id)
            log.info(f"Đã tạo mới calibration profile '{cal.profile_name}' (ID: {inserted_id})")

        # Tạo file JSON backup
        backup_path = Path(backup_dir) / f"calibration_{cal.profile_name}.json"
        log.debug(f"Đang ghi file backup: {backup_path}")
        backup_path.write_text(json.dumps(doc, default=str, indent=2))
        log.info(f"Đã lưu file backup: {backup_path}")

        buoc_thanh_cong("Lưu calibration", profile=cal.profile_name, id=inserted_id)
        return inserted_id

    except Exception as e:
        bao_cao = tao_bao_cao_loi(e, module="calibration/wizard.py")
        log.error(f"Lỗi khi lưu calibration: {e}")
        log.error(bao_cao)
        raise
