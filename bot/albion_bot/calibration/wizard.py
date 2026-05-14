from __future__ import annotations
import json
import sys
import time
from pathlib import Path

import click
from Xlib import display as xdisplay, X
from Xlib.ext import record
from Xlib.protocol import rq

from albion_bot.calibration.models import Calibration, Cell, InventoryConfig, Rect, Regions
from albion_bot.calibration.screen import get_screen_size
from albion_bot.db.connection import get_db
from albion_bot.platform.base import get_platform


# ---------------------------------------------------------------------------
# Mouse click capture via Xlib RECORD extension
# ---------------------------------------------------------------------------

def _wait_for_click() -> tuple[int, int]:
    """Block until the user clicks the left mouse button; return (x, y)."""
    local_dpy = xdisplay.Display()
    record_dpy = xdisplay.Display()

    result: list[tuple[int, int]] = []

    def handler(reply):
        data = reply.data
        while len(data):
            event, data = rq.EventField(None).parse(data, record_dpy)
            if event.type == X.ButtonPress and event.detail == 1:
                result.append((event.root_x, event.root_y))

    ctx = record_dpy.record_create_context(
        0,
        [record.AllClients],
        [{
            "core_requests": (0, 0),
            "core_replies": (0, 0),
            "ext_requests": (0, 0, 0, 0),
            "ext_replies": (0, 0, 0, 0),
            "delivered_events": (0, 0),
            "device_events": (X.ButtonPressMask, X.ButtonPressMask),
            "errors": (0, 0),
            "client_started": False,
            "client_died": False,
        }],
    )

    record_dpy.record_enable_context(ctx, handler)
    record_dpy.record_free_context(ctx)

    local_dpy.close()
    record_dpy.close()
    return result[0]


def _prompt_click(label: str) -> tuple[int, int]:
    click.echo(f"  → Move your mouse to {label} and LEFT-CLICK it. Waiting...")
    time.sleep(0.3)
    x, y = _wait_for_click()
    click.echo(f"    Captured: ({x}, {y})")
    return x, y


def _prompt_rect(label: str, default_w: int = 200, default_h: int = 40) -> Rect:
    """Capture top-left corner click; ask for width/height."""
    x, y = _prompt_click(f"the TOP-LEFT corner of {label}")
    w = click.prompt(f"    Width of {label} region (px)", default=default_w, type=int)
    h = click.prompt(f"    Height of {label} region (px)", default=default_h, type=int)
    return Rect(x=x, y=y, w=w, h=h)


# ---------------------------------------------------------------------------
# Cell grid computation
# ---------------------------------------------------------------------------

def _compute_cells(first: Rect, last: Rect, rows: int, cols: int) -> list[Cell]:
    total = rows * cols
    if total <= 1:
        return [Cell(index=0, x=first.x, y=first.y)]

    x_step = (last.x - first.x) / (cols - 1) if cols > 1 else 0
    y_step = (last.y - first.y) / (rows - 1) if rows > 1 else 0

    cells = []
    for i in range(total):
        row = i // cols
        col = i % cols
        cells.append(Cell(
            index=i,
            x=round(first.x + col * x_step),
            y=round(first.y + row * y_step),
        ))
    return cells


# ---------------------------------------------------------------------------
# Wizard entry point
# ---------------------------------------------------------------------------

def run_wizard(profile_name: str = "default") -> Calibration:
    click.echo("\n=== Albion Auto-Seller Calibration Wizard ===")
    click.echo("Make sure Albion Online is open and visible on screen.\n")

    platform = get_platform()
    screen = get_screen_size()
    click.echo(f"Platform: {platform}  |  Screen: {screen['width']}x{screen['height']}\n")

    # Grid layout
    rows = click.prompt("Inventory rows", default=8, type=int)
    cols = click.prompt("Inventory columns", default=6, type=int)
    click.echo()

    # Inventory cells
    click.echo("--- Inventory grid ---")
    fc_x, fc_y = _prompt_click("the CENTER of the FIRST inventory cell (top-left)")
    fc_w = click.prompt("    Cell width (px)", default=50, type=int)
    fc_h = click.prompt("    Cell height (px)", default=50, type=int)
    first_cell = Rect(x=fc_x, y=fc_y, w=fc_w, h=fc_h)

    lc_x, lc_y = _prompt_click("the CENTER of the LAST inventory cell (bottom-right)")
    last_cell = Rect(x=lc_x, y=lc_y, w=fc_w, h=fc_h)

    cells = _compute_cells(first_cell, last_cell, rows, cols)
    click.echo(f"    Computed {len(cells)} cell positions.\n")

    # UI regions
    click.echo("--- UI regions (click top-left corner of each region) ---")
    regions = Regions(
        sell_now_button=_prompt_rect("the SELL NOW button", default_w=120, default_h=35),
        buy_order_price=_prompt_rect("the BUY ORDER PRICE area", default_w=150, default_h=30),
        tooltip_item_name=_prompt_rect("the ITEM NAME in tooltip", default_w=250, default_h=25),
        tooltip_est_price=_prompt_rect("the ESTIMATED PRICE in tooltip", default_w=150, default_h=25),
        disconnect_icon=_prompt_rect("the DISCONNECT icon", default_w=40, default_h=40),
        popup_close=_prompt_rect("the POPUP CLOSE button", default_w=30, default_h=30),
        sort_button=_prompt_rect("the SORT button", default_w=80, default_h=30),
        stack_button=_prompt_rect("the STACK button", default_w=80, default_h=30),
        empty_slot_sample=_prompt_rect("an EMPTY inventory slot (for color reference)", default_w=10, default_h=10),
    )

    calibration = Calibration(
        profile_name=profile_name,
        platform=platform,
        screen=screen,
        inventory=InventoryConfig(
            rows=rows,
            cols=cols,
            first_cell=first_cell,
            last_cell=last_cell,
            cells=cells,
        ),
        regions=regions,
    )

    return calibration


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def save_calibration(cal: Calibration, backup_dir: str = ".") -> str:
    db = get_db()
    doc = cal.model_dump()

    existing = db.calibrations.find_one({"profile_name": cal.profile_name})
    if existing:
        db.calibrations.replace_one({"_id": existing["_id"]}, doc)
        inserted_id = str(existing["_id"])
    else:
        result = db.calibrations.insert_one(doc)
        inserted_id = str(result.inserted_id)

    # JSON backup
    backup_path = Path(backup_dir) / f"calibration_{cal.profile_name}.json"
    backup_path.write_text(json.dumps(doc, default=str, indent=2))

    return inserted_id
