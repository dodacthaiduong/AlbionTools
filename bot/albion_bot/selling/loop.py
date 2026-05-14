from __future__ import annotations
import logging
import time
from datetime import datetime, timezone

from albion_bot.calibration.models import Calibration
from albion_bot.db.connection import get_db
from albion_bot.inventory.models import ScannedSlot
from albion_bot.inventory.scanner import scan_inventory
from albion_bot.platform.base import get_input_backend
from albion_bot.selling.market import try_sell_item, wait_for_disconnect_clear
from albion_bot.selling.detection import is_disconnect_visible
from albion_bot.selling.models import BotSession, SessionStats, Transaction

log = logging.getLogger(__name__)


def _load_calibration_for_loop(profile: str) -> Calibration:
    db = get_db()
    doc = db.calibrations.find_one({"profile_name": profile})
    if not doc:
        raise RuntimeError(f"No calibration for profile '{profile}'. Run `calibrate` first.")
    doc.pop("_id", None)
    return Calibration.model_validate(doc)


def _get_min_price(slot: ScannedSlot) -> int | None:
    db = get_db()
    doc = db.item_configs.find_one({
        "base_name": slot.base_name,
        "tier": slot.tier,
        "enchant": slot.enchant,
    })
    if not doc:
        return None
    return doc.get("min_sell_price")


def _save_transaction(tx: Transaction) -> None:
    db = get_db()
    db.transactions.insert_one(tx.model_dump())


def _create_session(cal_profile: str) -> tuple[str, BotSession]:
    db = get_db()
    session = BotSession()
    result = db.bot_sessions.insert_one(session.model_dump())
    session_id = str(result.inserted_id)
    return session_id, session


def _update_session(session_id: str, stats: SessionStats, status: str = "running", stop_reason: str | None = None) -> None:
    db = get_db()
    update: dict = {
        "stats": stats.model_dump(),
        "status": status,
    }
    if stop_reason:
        update["stop_reason"] = stop_reason
    if status in ("stopped", "error"):
        update["ended_at"] = datetime.now(timezone.utc)
    db.bot_sessions.update_one({"_id": session_id}, {"$set": update})


def _click_sort_and_stack(cal: Calibration, backend) -> None:
    r = cal.regions.sort_button
    backend.click(r.x + r.w // 2, r.y + r.h // 2)
    time.sleep(0.4)
    r = cal.regions.stack_button
    backend.click(r.x + r.w // 2, r.y + r.h // 2)
    time.sleep(0.4)


def run_sell_loop(profile: str = "default", stop_flag: list[bool] | None = None) -> None:
    """
    Main sell loop. Runs until stop_flag[0] is True or an unrecoverable error occurs.
    stop_flag is a mutable list so the CLI can set it from a signal handler.
    """
    if stop_flag is None:
        stop_flag = [False]

    cal = _load_calibration_for_loop(profile)
    backend = get_input_backend()
    session_id, session = _create_session(profile)
    stats = SessionStats()

    log.info(f"Session {session_id} started.")

    try:
        while not stop_flag[0]:
            # Phase 1: scan inventory
            log.info("Phase 1: scanning inventory...")
            if is_disconnect_visible(cal.regions.disconnect_icon):
                wait_for_disconnect_clear(cal)

            slots = scan_inventory(profile=profile)
            filled = [s for s in slots if not s.empty]

            # Phase 2: sell each item
            log.info(f"Phase 2: selling {len(filled)} items...")
            for slot in filled:
                if stop_flag[0]:
                    break

                if is_disconnect_visible(cal.regions.disconnect_icon):
                    wait_for_disconnect_clear(cal)

                min_price = _get_min_price(slot)
                if min_price is None:
                    log.info(f"Slot {slot.slot} ({slot.full_name}): no min_sell_price set, skipping.")
                    continue

                try:
                    tx = try_sell_item(slot, session_id, cal, backend, min_price)
                    if tx:
                        _save_transaction(tx)
                        stats.items_sold += 1
                        stats.total_revenue += tx.total_price
                except Exception as e:
                    log.error(f"Slot {slot.slot}: error during sell — {e}")
                    stats.errors_count += 1

            # Phase 3: sort + stack
            log.info("Phase 3: sort + stack...")
            _click_sort_and_stack(cal, backend)

            stats.cycles_completed += 1
            _update_session(session_id, stats)
            log.info(f"Cycle {stats.cycles_completed} complete. Revenue so far: {stats.total_revenue}")

    except KeyboardInterrupt:
        log.info("Interrupted by user.")
        stop_flag[0] = True
    except Exception as e:
        log.error(f"Unrecoverable error: {e}")
        _update_session(session_id, stats, status="error", stop_reason="error")
        raise
    finally:
        if not stop_flag[0]:
            _update_session(session_id, stats, status="stopped", stop_reason="user_requested")
        else:
            _update_session(session_id, stats, status="stopped", stop_reason="user_requested")
        log.info(f"Session {session_id} ended. Stats: {stats}")
