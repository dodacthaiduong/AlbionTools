from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

from bson import ObjectId

from albion_bot.calibration.models import Calibration
from albion_bot.db.connection import get_db
from albion_bot.debug_logger import (
    DEBUG_MODE,
    buoc_thanh_cong,
    cap_nhat_buoc,
    tao_bao_cao_loi,
)
from albion_bot.inventory.models import ScannedSlot
from albion_bot.inventory.scanner import scan_inventory
from albion_bot.platform.base import get_input_backend
from albion_bot.selling.detection import is_disconnect_visible
from albion_bot.selling.market import try_sell_item, wait_for_disconnect_clear
from albion_bot.selling.models import BotSession, SessionStats, Transaction

log = logging.getLogger(__name__)


def _load_calibration_for_loop(profile: str) -> Calibration:
    log.debug(f"Đang tải cấu hình calibration cho profile '{profile}'...")
    cap_nhat_buoc(f"Tải calibration profile '{profile}'", profile=profile)
    db = get_db()
    doc = db.calibrations.find_one({"profile_name": profile})
    if not doc:
        raise RuntimeError(
            f"Không tìm thấy calibration cho profile '{profile}'. Hãy chạy lệnh `calibrate` trước."
        )
    doc.pop("_id", None)
    cal = Calibration.model_validate(doc)
    buoc_thanh_cong(f"Tải calibration profile '{profile}'", profile=profile)
    log.debug(f"Đã tải calibration thành công: platform={cal.platform}, màn hình={cal.screen}")
    return cal


def _get_min_price(slot: ScannedSlot) -> int | None:
    log.debug(f"Đang tra cứu giá tối thiểu cho vật phẩm: {slot.full_name} (T{slot.tier}.{slot.enchant})")
    db = get_db()
    doc = db.item_configs.find_one(
        {
            "base_name": slot.base_name,
            "tier": slot.tier,
            "enchant": slot.enchant,
        }
    )
    if not doc:
        log.debug(f"Không tìm thấy cấu hình giá cho: {slot.full_name}")
        return None
    min_price = doc.get("min_sell_price")
    if min_price is not None and doc.get("estimated_price"):
        if min_price < doc["estimated_price"] * 0.5:
            log.warning(
                f"CẢNH BÁO: {slot.full_name} — giá tối thiểu {min_price} thấp hơn 50% giá ước tính "
                f"{doc['estimated_price']} — có nguy cơ bán lỗ!"
            )
    log.debug(f"Giá tối thiểu cho {slot.full_name}: {min_price}")
    return min_price


def _save_inventory_snapshot(session_id: str, slots: list[ScannedSlot]) -> None:
    log.debug(f"Đang lưu ảnh chụp kho đồ cho phiên {session_id}...")
    cap_nhat_buoc("Lưu ảnh chụp kho đồ vào database", session_id=session_id)
    db = get_db()
    filled = [s for s in slots if not s.empty]
    items = [
        {
            "slot": s.slot,
            "config_id": "",
            "full_name": s.full_name,
            "tier": s.tier,
            "enchant": s.enchant,
            "quantity": s.quantity,
        }
        for s in filled
    ]
    total_est = sum(s.estimated_price or 0 for s in filled)
    snapshot = {
        "timestamp": datetime.now(timezone.utc),
        "session_id": session_id,
        "items": items,
        "empty_slots": len(slots) - len(filled),
        "total_estimated_value": total_est,
    }
    db.inventory_snapshots.insert_one(snapshot)
    buoc_thanh_cong("Lưu ảnh chụp kho đồ", so_vat_pham=len(filled), tong_gia_tri=total_est)
    log.debug(f"Đã lưu kho đồ: {len(filled)} vật phẩm, tổng giá trị ước tính: {total_est}")


def _save_transaction(tx: Transaction) -> None:
    log.debug(f"Đang lưu giao dịch: {tx.item.full_name} @ {tx.unit_price} tại {tx.market_city}")
    cap_nhat_buoc("Lưu giao dịch vào database", vat_pham=tx.item.full_name, gia=tx.unit_price)
    db = get_db()
    db.transactions.insert_one(tx.model_dump())
    buoc_thanh_cong("Lưu giao dịch", vat_pham=tx.item.full_name, gia=tx.unit_price)
    log.debug("Đã lưu giao dịch thành công.")


def _create_session(cal_profile: str) -> tuple[str, BotSession]:
    log.debug(f"Đang tạo phiên làm việc mới cho profile '{cal_profile}'...")
    cap_nhat_buoc("Tạo phiên làm việc mới", profile=cal_profile)
    db = get_db()
    session = BotSession()
    result = db.bot_sessions.insert_one(session.model_dump())
    session_id = str(result.inserted_id)
    buoc_thanh_cong("Tạo phiên làm việc", session_id=session_id)
    log.debug(f"Đã tạo phiên làm việc: ID={session_id}")
    return session_id, session


def _update_session(
    session_id: str,
    stats: SessionStats,
    status: str = "running",
    stop_reason: str | None = None,
) -> None:
    log.debug(f"Đang cập nhật trạng thái phiên {session_id}: status={status}")
    db = get_db()
    update: dict = {
        "stats": stats.model_dump(),
        "status": status,
    }
    if stop_reason:
        update["stop_reason"] = stop_reason
    if status in ("stopped", "error"):
        update["ended_at"] = datetime.now(timezone.utc)
    db.bot_sessions.update_one({"_id": ObjectId(session_id)}, {"$set": update})
    log.debug(f"Đã cập nhật phiên: đã bán={stats.items_sold}, doanh thu={stats.total_revenue}, lỗi={stats.errors_count}")


def _click_sort_and_stack(cal: Calibration, backend) -> None:
    log.debug("Đang nhấn nút sắp xếp kho đồ...")
    cap_nhat_buoc("Sắp xếp và gộp kho đồ")
    r = cal.regions.sort_button
    backend.click(r.x + r.w // 2, r.y + r.h // 2)
    time.sleep(0.4)
    log.debug("Đang nhấn nút gộp vật phẩm...")
    r = cal.regions.stack_button
    backend.click(r.x + r.w // 2, r.y + r.h // 2)
    time.sleep(0.4)
    buoc_thanh_cong("Sắp xếp và gộp kho đồ")


def run_sell_loop(
    profile: str = "default", stop_flag: list[bool] | None = None
) -> None:
    """
    Vòng lặp bán hàng chính. Chạy cho đến khi stop_flag[0] là True hoặc gặp lỗi không thể phục hồi.
    stop_flag là list có thể thay đổi để CLI có thể dừng từ signal handler.
    """
    if stop_flag is None:
        stop_flag = [False]

    log.info("=== BẮT ĐẦU VÒNG LẶP BÁN HÀNG ===")
    log.info(f"Profile đang dùng: '{profile}'")
    if DEBUG_MODE:
        log.debug("[DEBUG] Chế độ debug đang bật — mọi bước sẽ được ghi chi tiết")

    cap_nhat_buoc("Khởi động vòng lặp bán hàng", profile=profile)
    cal = _load_calibration_for_loop(profile)

    log.info("Đang khởi tạo bộ điều khiển chuột/bàn phím...")
    cap_nhat_buoc("Khởi tạo input backend")
    backend = get_input_backend()
    buoc_thanh_cong("Khởi tạo input backend")

    session_id, session = _create_session(profile)
    stats = SessionStats()

    log.info(f"Phiên làm việc {session_id} đã bắt đầu.")

    _error_occurred = False
    try:
        while not stop_flag[0]:
            log.info(f"--- Chu kỳ {stats.cycles_completed + 1} bắt đầu ---")

            # Giai đoạn 1: quét kho đồ
            log.info("Giai đoạn 1: Đang quét kho đồ...")
            cap_nhat_buoc("Quét kho đồ", chu_ky=stats.cycles_completed + 1)
            if is_disconnect_visible(cal.regions.disconnect_icon):
                log.warning("Phát hiện mất kết nối — đang chờ kết nối lại...")
                wait_for_disconnect_clear(cal)

            slots = scan_inventory(profile=profile)
            filled = [s for s in slots if not s.empty]
            log.info(f"Quét xong: {len(filled)} vật phẩm, {len(slots) - len(filled)} ô trống")
            _save_inventory_snapshot(session_id, slots)
            buoc_thanh_cong("Quét kho đồ", so_vat_pham=len(filled))

            # Giai đoạn 2: bán từng vật phẩm
            log.info(f"Giai đoạn 2: Đang bán {len(filled)} vật phẩm...")
            for slot in filled:
                if stop_flag[0]:
                    log.info("Nhận tín hiệu dừng — kết thúc chu kỳ hiện tại.")
                    break

                if is_disconnect_visible(cal.regions.disconnect_icon):
                    log.warning("Mất kết nối trong khi bán — đang chờ kết nối lại...")
                    wait_for_disconnect_clear(cal)

                log.debug(f"Đang xử lý ô {slot.slot}: {slot.full_name} (T{slot.tier}.{slot.enchant})")
                cap_nhat_buoc(f"Bán vật phẩm ô {slot.slot}", vat_pham=slot.full_name)

                min_price = _get_min_price(slot)
                if min_price is None:
                    log.info(
                        f"Ô {slot.slot} ({slot.full_name}): chưa đặt giá tối thiểu — bỏ qua."
                    )
                    continue

                try:
                    tx = try_sell_item(slot, session_id, cal, backend, min_price)
                    if tx:
                        _save_transaction(tx)
                        stats.items_sold += 1
                        stats.total_revenue += tx.total_price
                        log.info(f"✓ Đã bán: {slot.full_name} @ {tx.unit_price} tại {tx.market_city}")
                    else:
                        log.debug(f"Ô {slot.slot}: bỏ qua (giá không đạt hoặc không có lệnh mua)")
                except Exception as e:
                    stats.errors_count += 1
                    bao_cao = tao_bao_cao_loi(e, module="selling/loop.py")
                    log.error(f"Lỗi khi bán ô {slot.slot} ({slot.full_name}): {e}")
                    log.error(bao_cao)

            # Giai đoạn 3: sắp xếp + gộp
            log.info("Giai đoạn 3: Đang sắp xếp và gộp kho đồ...")
            _click_sort_and_stack(cal, backend)

            stats.cycles_completed += 1
            _update_session(session_id, stats)
            log.info(
                f"Chu kỳ {stats.cycles_completed} hoàn thành. "
                f"Đã bán: {stats.items_sold} vật phẩm | "
                f"Doanh thu: {stats.total_revenue:,} | "
                f"Lỗi: {stats.errors_count}"
            )

    except KeyboardInterrupt:
        log.info("Người dùng yêu cầu dừng bot.")
        stop_flag[0] = True
    except Exception as e:
        bao_cao = tao_bao_cao_loi(e, module="selling/loop.py")
        log.error(f"Lỗi nghiêm trọng không thể tiếp tục: {e}")
        log.error(bao_cao)
        _update_session(session_id, stats, status="error", stop_reason="error")
        _error_occurred = True
        raise
    finally:
        if not _error_occurred:
            _update_session(
                session_id, stats, status="stopped", stop_reason="user_requested"
            )
        log.info(
            f"=== KẾT THÚC PHIÊN {session_id} === "
            f"Chu kỳ: {stats.cycles_completed} | "
            f"Đã bán: {stats.items_sold} | "
            f"Doanh thu: {stats.total_revenue:,} | "
            f"Lỗi: {stats.errors_count}"
        )
