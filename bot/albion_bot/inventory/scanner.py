from __future__ import annotations
import time
import random
from datetime import datetime, timezone

import click

from albion_bot.calibration.models import Calibration
from albion_bot.calibration.screen import get_pixel_color
from albion_bot.db.connection import get_db
from albion_bot.inventory.empty_slot import is_empty_slot, sample_reference_color
from albion_bot.inventory.models import ItemConfig, ScannedSlot
from albion_bot.ocr.reader import parse_item_name, read_price, read_text
from albion_bot.platform.base import get_input_backend


def _load_calibration(profile: str = "default") -> Calibration:
    db = get_db()
    doc = db.calibrations.find_one({"profile_name": profile})
    if not doc:
        raise RuntimeError(f"No calibration found for profile '{profile}'. Run `calibrate` first.")
    doc.pop("_id", None)
    return Calibration.model_validate(doc)


def _upsert_item_config(slot: ScannedSlot) -> None:
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
            "min_sell_price": None,
            "enabled": True,
            "created_at": now,
        },
    }
    db.item_configs.update_one(key, update, upsert=True)


def scan_inventory(profile: str = "default") -> list[ScannedSlot]:
    cal = _load_calibration(profile)
    backend = get_input_backend()
    regions = cal.regions
    cells = cal.inventory.cells

    ref_color = sample_reference_color(regions.empty_slot_sample)
    click.echo(f"Empty slot reference color: {ref_color}")

    results: list[ScannedSlot] = []

    for cell in cells:
        # Check empty before clicking
        sample_rect = regions.empty_slot_sample.model_copy(update={"x": cell.x, "y": cell.y})
        if is_empty_slot(sample_rect, ref_color):
            results.append(ScannedSlot(
                slot=cell.index, full_name="", base_name="",
                tier=0, enchant=0, quantity=0, empty=True,
            ))
            continue

        # Click slot to open detail panel
        backend.click(cell.x, cell.y)
        time.sleep(random.uniform(0.3, 0.5))

        # OCR reads
        raw_name = read_text(regions.tooltip_item_name)
        est_price = read_price(regions.tooltip_est_price)

        if not raw_name:
            click.echo(f"  Slot {cell.index}: OCR returned empty name, skipping.")
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
            quantity=1,  # quantity read during sell phase; 1 is placeholder
            estimated_price=est_price,
            empty=False,
        )
        results.append(slot)
        _upsert_item_config(slot)

        click.echo(f"  Slot {cell.index}: {raw_name} (T{tier}.{enchant}) ~{est_price}")
        time.sleep(random.uniform(0.1, 0.2))

    filled = [s for s in results if not s.empty]
    click.echo(f"\nScan complete: {len(filled)} items, {len(results) - len(filled)} empty slots.")
    return results
