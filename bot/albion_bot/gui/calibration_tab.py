from __future__ import annotations

import queue
import threading
import time
from datetime import datetime, timezone
from typing import Optional

import customtkinter as ctk

from albion_bot.calibration.models import (
    Calibration,
    Cell,
    InventoryConfig,
    Rect,
    Regions,
)
from albion_bot.calibration.screen import capture_region, get_screen_size
from albion_bot.calibration.wizard import _compute_cells, save_calibration
from albion_bot.gui.overlay import SelectionOverlay
from albion_bot.gui.widgets import LogBox, RegionPreview
from albion_bot.platform.base import get_input_backend, get_platform

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _human(key: str) -> str:
    """Convert a snake_case region key to a Title Case label."""
    return key.replace("_", " ").title()


# Region keys in display order
_REGION_KEYS: list[str] = [
    "lowest_sell_order_price",
    "sell_order_price_input",
    "sell_order_confirm_button",
    "my_orders_tab",
    "my_orders_list",
    "tooltip_item_name",
    "tooltip_est_price",
    "disconnect_icon",
    "popup_close",
    "sort_button",
    "stack_button",
    "empty_slot_sample",
]


# ---------------------------------------------------------------------------
# Per-region row widget
# ---------------------------------------------------------------------------


class _RegionRow:
    """Holds all widgets and state for a single region selection row."""

    def __init__(
        self,
        parent: ctk.CTkFrame,
        label: str,
        on_select: "callable[[_RegionRow], None]",
    ) -> None:
        self.rect: Optional[Rect] = None
        self.label_text = label

        self.frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.frame.pack(fill="x", padx=8, pady=3)

        # label
        ctk.CTkLabel(self.frame, text=label, width=200, anchor="w").grid(
            row=0, column=0, sticky="w", padx=(0, 8)
        )

        # select button
        ctk.CTkButton(
            self.frame,
            text="Select Region",
            width=120,
            command=lambda: on_select(self),
        ).grid(row=0, column=1, padx=(0, 8))

        # coordinate display
        self._coord_label = ctk.CTkLabel(
            self.frame, text="—", width=180, anchor="w", text_color="gray"
        )
        self._coord_label.grid(row=0, column=2, padx=(0, 8))

        # thumbnail preview
        self._preview = RegionPreview(self.frame)
        self._preview.grid(row=0, column=3, padx=(0, 4))

    def update(self, rect: Rect, png_bytes: bytes) -> None:
        self.rect = rect
        self._coord_label.configure(
            text=f"x={rect.x}  y={rect.y}  {rect.w}×{rect.h}",
            text_color="white",
        )
        self._preview.update_image(png_bytes)

    def get_rect(self) -> Optional[Rect]:
        return self.rect


# ---------------------------------------------------------------------------
# CalibrationTab
# ---------------------------------------------------------------------------


class CalibrationTab:
    """Calibration wizard tab."""

    def __init__(self, parent: ctk.CTkFrame) -> None:
        self._parent = parent

        self._scroll = ctk.CTkScrollableFrame(parent)
        self._scroll.pack(fill="both", expand=True, padx=4, pady=4)

        self._grid_row: Optional[_RegionRow] = None
        self._region_rows: dict[str, _RegionRow] = {}
        self._log_queue: queue.Queue[str] = queue.Queue()

        self._build_top_row()
        self._build_inventory_section()
        self._build_regions_section()
        self._build_save_button()
        self._build_log_box()

    # ------------------------------------------------------------------
    # Layout builders
    # ------------------------------------------------------------------

    def _build_top_row(self) -> None:
        frame = ctk.CTkFrame(self._scroll, fg_color="transparent")
        frame.pack(fill="x", padx=8, pady=(8, 4))

        ctk.CTkLabel(frame, text="Profile name:").grid(
            row=0, column=0, sticky="w", padx=(0, 6)
        )
        self._profile_entry = ctk.CTkEntry(frame, width=160)
        self._profile_entry.insert(0, "default")
        self._profile_entry.grid(row=0, column=1, padx=(0, 24))

        ctk.CTkLabel(frame, text="Rows:").grid(row=0, column=2, sticky="w", padx=(0, 4))
        self._rows_entry = ctk.CTkEntry(frame, width=50)
        self._rows_entry.insert(0, "8")
        self._rows_entry.grid(row=0, column=3, padx=(0, 16))

        ctk.CTkLabel(frame, text="Cols:").grid(row=0, column=4, sticky="w", padx=(0, 4))
        self._cols_entry = ctk.CTkEntry(frame, width=50)
        self._cols_entry.insert(0, "6")
        self._cols_entry.grid(row=0, column=5)

    def _build_inventory_section(self) -> None:
        ctk.CTkLabel(
            self._scroll,
            text="Inventory Grid",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=8, pady=(12, 2))

        ctk.CTkLabel(
            self._scroll,
            text="Select the entire inventory grid area. Cells will be computed automatically from rows × cols.",
            anchor="w",
            text_color="gray",
            wraplength=700,
        ).pack(fill="x", padx=8, pady=(0, 6))

        self._grid_row = _RegionRow(
            self._scroll,
            label="Inventory Grid Area",
            on_select=self._on_select,
        )

        # Test clicks button row
        test_frame = ctk.CTkFrame(self._scroll, fg_color="transparent")
        test_frame.pack(fill="x", padx=8, pady=(2, 4))

        self._test_btn = ctk.CTkButton(
            test_frame,
            text="Test Clicks",
            width=120,
            fg_color="#1565c0",
            hover_color="#0d47a1",
            command=self._on_test_clicks,
        )
        self._test_btn.pack(side="left", padx=(0, 12))

        ctk.CTkLabel(
            test_frame,
            text="Clicks every cell — stops at first empty slot. Empty Slot Sample must be selected.",
            text_color="gray",
            anchor="w",
            wraplength=500,
        ).pack(side="left")

    def _build_regions_section(self) -> None:
        ctk.CTkLabel(
            self._scroll,
            text="UI Regions",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=8, pady=(12, 2))

        for key in _REGION_KEYS:
            row = _RegionRow(
                self._scroll,
                label=_human(key),
                on_select=self._on_select,
            )
            self._region_rows[key] = row

    def _build_save_button(self) -> None:
        ctk.CTkButton(
            self._scroll,
            text="Save Calibration",
            command=self._on_save,
            fg_color="#2a7a2a",
            hover_color="#1f5c1f",
        ).pack(pady=(16, 4))

    def _build_log_box(self) -> None:
        self._log = LogBox(self._scroll)
        self._log.pack(fill="x", padx=8, pady=(4, 8))
        self._drain_log_queue()

    def _drain_log_queue(self) -> None:
        """Drain the thread-safe log queue on the main thread."""
        try:
            while True:
                msg = self._log_queue.get_nowait()
                self._log.log(msg)
        except queue.Empty:
            pass
        self._scroll.after(50, self._drain_log_queue)

    def _tlog(self, msg: str) -> None:
        """Thread-safe log — safe to call from any thread."""
        self._log_queue.put(msg)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_test_clicks(self) -> None:
        """Compute cells from current grid rect and click each one.

        Requires the empty_slot_sample region to be selected. The reference
        color is sampled AFTER the 2 s delay (while the game is visible).
        Stops at the first empty slot.
        """
        grid_rect = self._grid_row.get_rect() if self._grid_row else None
        if grid_rect is None:
            self._log.log("ERROR: Select the Inventory Grid Area first.")
            return

        empty_slot_row = self._region_rows.get("empty_slot_sample")
        empty_slot_rect = empty_slot_row.get_rect() if empty_slot_row else None
        if empty_slot_rect is None:
            self._log.log(
                "ERROR: Empty Slot Sample region not selected. "
                "Select it in the UI Regions section first."
            )
            return

        try:
            rows = int(self._rows_entry.get())
            cols = int(self._cols_entry.get())
        except ValueError:
            self._log.log("ERROR: Rows and Cols must be integers.")
            return

        cells = _compute_cells(grid_rect, rows, cols)
        self._log.log(f"Testing {len(cells)} cells ({rows}×{cols}) — starting in 2 s …")
        self._log.log("  Switch to Albion now. Test stops at first empty slot.")

        from albion_bot.inventory.empty_slot import (
            is_empty_slot,
            sample_reference_color,
        )

        def _run() -> None:
            try:
                time.sleep(2)

                # Sample reference color now — game window is in focus
                ref_color = sample_reference_color(empty_slot_rect)
                self._tlog(f"  Empty slot reference color: RGB{ref_color}")

                backend = get_input_backend()
                clicked = 0
                for cell in cells:
                    probe = Rect(
                        x=cell.x, y=cell.y, w=empty_slot_rect.w, h=empty_slot_rect.h
                    )
                    if is_empty_slot(probe, ref_color):
                        self._tlog(
                            f"  Cell {cell.index:>2} is empty — stopping. "
                            f"({clicked} filled slots found)"
                        )
                        return

                    backend.click(cell.x, cell.y)
                    clicked += 1
                    self._tlog(f"  Clicked cell {cell.index:>2}  ({cell.x}, {cell.y})")
                    time.sleep(0.15)

                self._tlog(
                    f"Test complete — all {clicked} cells clicked, no empty slot found."
                )
            except Exception as exc:
                self._tlog(f"ERROR during test: {exc}")

        threading.Thread(target=_run, daemon=True, name="cell-test").start()

    def _on_select(self, row: _RegionRow) -> None:
        self._log.log(f"Selecting region for: {row.label_text} …")
        # Short delay so the main window redraws before the overlay appears
        self._parent.after(100, lambda: self._run_overlay(row))

    def _run_overlay(self, row: _RegionRow) -> None:
        rect = SelectionOverlay().ask_region(self._parent)
        if rect is None:
            self._log.log(f"  Cancelled — {row.label_text}")
            return
        try:
            png_bytes = capture_region(rect)
            row.update(rect, png_bytes)
            self._log.log(
                f"  {row.label_text}: x={rect.x}, y={rect.y}, {rect.w}×{rect.h}"
            )
        except Exception as exc:
            self._log.log(f"  Screenshot failed: {exc}")
            row.rect = rect
            row._coord_label.configure(
                text=f"x={rect.x}  y={rect.y}  {rect.w}×{rect.h}",
                text_color="white",
            )

    def _on_save(self) -> None:
        self._log.log("Saving calibration …")

        # profile / grid params
        profile_name = self._profile_entry.get().strip() or "default"
        try:
            rows = int(self._rows_entry.get())
            cols = int(self._cols_entry.get())
        except ValueError:
            self._log.log("ERROR: Rows and Cols must be integers.")
            return

        # inventory grid rect
        grid_rect = self._grid_row.get_rect() if self._grid_row else None
        if grid_rect is None:
            self._log.log("ERROR: Inventory Grid Area has not been selected.")
            return

        cells: list[Cell] = _compute_cells(grid_rect, rows, cols)

        # UI regions
        missing: list[str] = []
        region_rects: dict[str, Rect] = {}
        for key in _REGION_KEYS:
            r = self._region_rows[key].get_rect()
            if r is None:
                missing.append(_human(key))
            else:
                region_rects[key] = r

        if missing:
            self._log.log("ERROR: The following regions have not been selected:")
            for m in missing:
                self._log.log(f"  • {m}")
            return

        regions = Regions(**region_rects)

        now = datetime.now(timezone.utc)
        cal = Calibration(
            profile_name=profile_name,
            platform=get_platform(),
            screen=get_screen_size(),
            inventory=InventoryConfig(
                rows=rows,
                cols=cols,
                grid_rect=grid_rect,
                cells=cells,
            ),
            regions=regions,
            created_at=now,
            updated_at=now,
        )

        try:
            inserted_id = save_calibration(cal, backup_dir=".")
            self._log.log(f"Saved — profile '{profile_name}', id={inserted_id}")
            self._log.log(f"Computed {len(cells)} cell positions ({rows}×{cols}).")
        except Exception as exc:
            self._log.log(f"ERROR saving calibration: {exc}")
