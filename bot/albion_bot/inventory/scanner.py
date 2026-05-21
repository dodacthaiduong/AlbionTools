from __future__ import annotations
import logging
import time
import random
from datetime import datetime, timezone

import click

from albion_bot.calibration.models import Calibration
from albion_bot.calibration.screen import get_pixel_color
from albion_bot.db.connection import get_db
from albion_bot.debug_logger import DEBUG_MODE, buoc_thanh_cong, cap_nhat_buoc, tao_bao_cao_loi
from albion_bot.inventory.empty_slot import is_empty_slot, sample_reference_color
from albion_bot.inventory.models import ItemConfig, ScannedSlot
from albion_bot.ocr.reader import parse_item_name, read_price, read_text
from albion_bot.platform.base import get_input_backend

log = logging.getLogger(__name__)


def _load_calibration(profile: str = "default") -> Calibration:
    log.debug(f"Đang tải calibration cho profile '{profile}'...")
    cap_nhat_buoc(f"Tải calibration '{profile}'", profile=profile)
    db = get_db()
    doc = db.calibrations.find_one({"profile_name": profile})
    if not doc:
        raise RuntimeError(f"Không tìm thấy calibration cho profile '{profile}'. Hãy chạy lệnh `calibrate` trước.")
    doc.pop("_id", None)
    cal = Calibration.model_validate(doc)
    buoc_thanh_cong(f"Tải calibration '{profile}'")
    log.debug(f"Calibration đã tải: {cal.inventory.rows} hàng x {cal.inventory.cols} cột = {len(cal.inventory.cells)} ô")
    return cal


def _upsert_item_config(slot: ScannedSlot) -> None:
    log.debug(f"Đang cập nhật cấu hình vật phẩm: {slot.full_name}")
    db = get_db()
    now = datetime.now(timezone.utc)
    key = {"base_name": slot.base_name, "tier": slot.tier, "enchant": slot.enchant}
    update = {
        "$set": {
            "full_name": slot.full_name,
            "estimated_price": slot.estimated_price,
            "last_scanned_at": now,
            "updated_at": now,
        },
        "$setOnInsert": {
            "cost_price": None,
            "enabled": True,
            "created_at": now,
        },
    }
    db.item_configs.update_one(key, update, upsert=True)
    log.debug(f"Đã cập nhật cấu hình cho: {slot.full_name}")


def scan_inventory(profile: str = "default") -> list[ScannedSlot]:
    log.info("=== BẮT ĐẦU QUÉT KHO ĐỒ ===")
    cap_nhat_buoc("Quét kho đồ", profile=profile)

    cal = _load_calibration(profile)
    backend = get_input_backend()
    regions = cal.regions
    cells = cal.inventory.cells

    log.info(f"Tổng số ô cần quét: {len(cells)}")

    try:
        ref_color = sample_reference_color(regions.empty_slot_sample)
        log.debug(f"Màu tham chiếu ô trống: RGB{ref_color}")
        click.echo(f"Màu tham chiếu ô trống: {ref_color}")
    except Exception as e:
        bao_cao = tao_bao_cao_loi(e, module="inventory/scanner.py")
        log.error(f"Không lấy được màu tham chiếu ô trống: {e}")
        log.error(bao_cao)
        raise

    results: list[ScannedSlot] = []
    so_o_trong = 0
    so_o_co_do = 0

    for cell in cells:
        cap_nhat_buoc(f"Quét ô {cell.index}", o=cell.index, x=cell.x, y=cell.y)

        # Kiểm tra ô trống trước khi click
        sample_rect = regions.empty_slot_sample.model_copy(update={"x": cell.x, "y": cell.y})
        if is_empty_slot(sample_rect, ref_color):
            so_o_trong += 1
            log.debug(f"Ô {cell.index}: trống — bỏ qua")
            results.append(ScannedSlot(
                slot=cell.index, full_name="", base_name="",
                tier=0, enchant=0, quantity=0, empty=True,
            ))
            continue

        # Click vào ô để mở bảng chi tiết
        log.debug(f"Ô {cell.index}: có đồ — đang click để đọc thông tin...")
        try:
            backend.click(cell.x, cell.y)
            time.sleep(random.uniform(0.3, 0.5))

            # Đọc OCR
            raw_name = read_text(regions.tooltip_item_name)
            est_price = read_price(regions.tooltip_est_price)

            if not raw_name:
                log.warning(f"Ô {cell.index}: OCR không đọc được tên vật phẩm — bỏ qua ô này.")
                click.echo(f"  Ô {cell.index}: OCR trả về tên rỗng, bỏ qua.")
                results.append(ScannedSlot(
                    slot=cell.index, full_name="", base_name="",
                    tier=0, enchant=0, quantity=0, empty=True,
                ))
                continue

            base_name, tier, enchant = parse_item_name(raw_name)
            slot = ScannedSlot(
                slot=cell.index,
                full_name=raw_name,
                base_name=base_name,
                tier=tier,
                enchant=enchant,
                quantity=1,
                estimated_price=est_price,
                empty=False,
            )
            results.append(slot)
            _upsert_item_config(slot)
            so_o_co_do += 1

            log.debug(f"Ô {cell.index}: {raw_name} (T{tier}.{enchant}) ~{est_price:,}" if est_price else f"Ô {cell.index}: {raw_name} (T{tier}.{enchant}) giá chưa rõ")
            click.echo(f"  Ô {cell.index}: {raw_name} (T{tier}.{enchant}) ~{est_price}")
            time.sleep(random.uniform(0.1, 0.2))

        except Exception as e:
            bao_cao = tao_bao_cao_loi(e, module="inventory/scanner.py")
            log.error(f"Lỗi khi quét ô {cell.index}: {e}")
            log.error(bao_cao)
            results.append(ScannedSlot(
                slot=cell.index, full_name="", base_name="",
                tier=0, enchant=0, quantity=0, empty=True,
            ))

    buoc_thanh_cong("Quét kho đồ", so_vat_pham=so_o_co_do, so_o_trong=so_o_trong)
    log.info(f"=== QUÉT XONG: {so_o_co_do} vật phẩm, {so_o_trong} ô trống ===")
    click.echo(f"\nQuét xong: {so_o_co_do} vật phẩm, {so_o_trong} ô trống.")
    return results
