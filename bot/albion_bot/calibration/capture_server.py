"""
Polls MongoDB calibration_commands for pending capture_click requests,
captures the mouse click, and writes the result back.
Run via: uv run python main.py calibrate-server
"""
from __future__ import annotations
import logging
import time

from albion_bot.calibration.wizard import _wait_for_click
from albion_bot.db.connection import get_db

log = logging.getLogger(__name__)


def run_capture_server() -> None:
    log.info("Calibration capture server started. Waiting for click requests...")
    db = get_db()
    col = db.calibration_commands

    while True:
        doc = col.find_one({"type": "capture_click", "status": "pending"})
        if doc:
            log.info(f"Capture request {doc['_id']} received. Waiting for click...")
            try:
                x, y = _wait_for_click()
                col.update_one(
                    {"_id": doc["_id"]},
                    {"$set": {"status": "done", "x": x, "y": y}},
                )
                log.info(f"Captured ({x}, {y}) for request {doc['_id']}")
            except Exception as e:
                log.error(f"Click capture failed: {e}")
                col.update_one(
                    {"_id": doc["_id"]},
                    {"$set": {"status": "error", "error": str(e)}},
                )
        time.sleep(0.2)
