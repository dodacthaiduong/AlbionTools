from __future__ import annotations

import logging
from typing import Any

import customtkinter as ctk

from albion_bot.db.connection import get_db
from albion_bot.gui.widgets import SectionLabel

log = logging.getLogger(__name__)


class _ItemRow:
    """Holds all widgets for a single item_config row."""

    def __init__(
        self, parent: ctk.CTkScrollableFrame, doc: dict[str, Any], on_save: callable
    ) -> None:
        self._doc = doc
        self._on_save = on_save

        tier = doc.get("tier", 0)
        enchant = doc.get("enchant", 0)
        tier_str = f"T{tier}.{enchant}" if enchant else f"T{tier}"
        est = doc.get("estimated_price")
        est_str = f"{est:,}" if est is not None else "—"
        cost_price = doc.get("cost_price", doc.get("min_sell_price"))

        self.frame = ctk.CTkFrame(parent, fg_color="transparent")

        # Full name
        self._name_label = ctk.CTkLabel(
            self.frame, text=doc.get("full_name", ""), anchor="w", width=220
        )
        self._name_label.grid(row=0, column=0, padx=(4, 8), pady=4, sticky="w")

        # Tier + enchant
        self._tier_label = ctk.CTkLabel(self.frame, text=tier_str, anchor="w", width=50)
        self._tier_label.grid(row=0, column=1, padx=(0, 8), pady=4, sticky="w")

        # Estimated price
        self._est_label = ctk.CTkLabel(self.frame, text=est_str, anchor="e", width=90)
        self._est_label.grid(row=0, column=2, padx=(0, 8), pady=4, sticky="e")

        # Cost price entry
        self._cost_entry = ctk.CTkEntry(
            self.frame, width=100, placeholder_text="cost price"
        )
        if cost_price is not None:
            self._cost_entry.insert(0, str(cost_price))
        self._cost_entry.grid(row=0, column=3, padx=(0, 8), pady=4)

        # Enabled switch
        self._enabled_var = ctk.BooleanVar(value=bool(doc.get("enabled", False)))
        self._switch = ctk.CTkSwitch(
            self.frame, text="Enabled", variable=self._enabled_var, width=90
        )
        self._switch.grid(row=0, column=4, padx=(0, 8), pady=4)

        # Save button
        self._save_btn = ctk.CTkButton(
            self.frame,
            text="Save",
            width=60,
            command=self._save,
        )
        self._save_btn.grid(row=0, column=5, padx=(0, 4), pady=4)

    def _save(self) -> None:
        raw = self._cost_entry.get().strip()
        cost_price: int | None = None
        if raw:
            try:
                cost_price = int(raw)
            except ValueError:
                self._on_save(
                    False, f"Invalid price '{raw}' for {self._doc.get('full_name')}"
                )
                return
        enabled = self._enabled_var.get()
        self._on_save(True, None, self._doc, cost_price, enabled)

    def matches(self, query: str) -> bool:
        """Return True if the item name contains *query* (case-insensitive)."""
        return query.lower() in self._doc.get("full_name", "").lower()

    def show(self) -> None:
        self.frame.pack(fill="x", padx=4, pady=1)

    def hide(self) -> None:
        self.frame.pack_forget()


class ConfigTab:
    """Item config tab — edit cost prices and enabled state for each item."""

    def __init__(self, parent: ctk.CTkFrame) -> None:
        self._parent = parent
        self._rows: list[_ItemRow] = []

        self._build_ui()
        self._load_items()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self._parent.grid_rowconfigure(1, weight=0)
        self._parent.grid_columnconfigure(0, weight=1)

        # ── Top bar ────────────────────────────────────────────────────
        top_bar = ctk.CTkFrame(self._parent, fg_color="transparent")
        top_bar.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 4))

        SectionLabel(top_bar, text="Item Configuration").pack(side="left", padx=(0, 16))

        self._refresh_btn = ctk.CTkButton(
            top_bar, text="Refresh", width=80, command=self._load_items
        )
        self._refresh_btn.pack(side="left", padx=(0, 12))

        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", self._on_search_changed)
        self._search_entry = ctk.CTkEntry(
            top_bar,
            textvariable=self._search_var,
            placeholder_text="Filter by name…",
            width=220,
        )
        self._search_entry.pack(side="left")

        # ── Column headers ─────────────────────────────────────────────
        header = ctk.CTkFrame(self._parent, fg_color="transparent")
        header.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 2))

        for col, (text, width) in enumerate(
            [
                ("Item Name", 220),
                ("Tier", 50),
                ("Est. Price", 90),
                ("Cost Price", 100),
                ("Enabled", 90),
                ("", 60),
            ]
        ):
            ctk.CTkLabel(
                header,
                text=text,
                anchor="w",
                width=width,
                font=ctk.CTkFont(size=11, weight="bold"),
            ).grid(
                row=0, column=col, padx=(4 if col == 0 else 0, 8), pady=2, sticky="w"
            )

        # ── Scrollable item list ───────────────────────────────────────
        self._scroll = ctk.CTkScrollableFrame(self._parent)
        self._scroll.grid(row=2, column=0, sticky="nsew", padx=12, pady=4)
        self._parent.grid_rowconfigure(2, weight=1)

        # ── Status bar ─────────────────────────────────────────────────
        self._status_label = ctk.CTkLabel(
            self._parent,
            text="",
            anchor="w",
            font=ctk.CTkFont(size=11),
        )
        self._status_label.grid(row=3, column=0, sticky="ew", padx=14, pady=(2, 8))

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def _load_items(self) -> None:
        self._set_status("Loading…")
        self._refresh_btn.configure(state="disabled")

        # Clear existing rows
        for row in self._rows:
            row.frame.destroy()
        self._rows.clear()

        try:
            db = get_db()
            docs = list(
                db.item_configs.find({}).sort(
                    [("tier", 1), ("enchant", 1), ("full_name", 1)]
                )
            )
        except Exception as exc:
            log.exception("Failed to load item configs")
            self._set_status(f"Error loading items: {exc}", error=True)
            self._refresh_btn.configure(state="normal")
            return

        query = self._search_var.get().strip()
        for doc in docs:
            row = _ItemRow(self._scroll, doc, self._handle_save)
            self._rows.append(row)
            if not query or row.matches(query):
                row.show()
            else:
                row.hide()

        self._set_status(f"Loaded {len(docs)} items.")
        self._refresh_btn.configure(state="normal")

    # ------------------------------------------------------------------
    # Filtering
    # ------------------------------------------------------------------

    def _on_search_changed(self, *_args: object) -> None:
        query = self._search_var.get().strip()
        for row in self._rows:
            if not query or row.matches(query):
                row.show()
            else:
                row.hide()

    # ------------------------------------------------------------------
    # Save callback
    # ------------------------------------------------------------------

    def _handle_save(
        self,
        success: bool,
        error_msg: str | None,
        doc: dict[str, Any] | None = None,
        cost_price: int | None = None,
        enabled: bool = True,
    ) -> None:
        if not success:
            self._set_status(error_msg or "Save failed.", error=True)
            return

        try:
            db = get_db()
            db.item_configs.update_one(
                {"_id": doc["_id"]},
                {
                    "$set": {
                        "cost_price": cost_price,
                        "enabled": enabled,
                    },
                    "$unset": {
                        "min_sell_price": "",
                    },
                },
            )
            name = doc.get("full_name", "item")
            self._set_status(f"Saved '{name}'.")
            log.info(
                "Saved item config for '%s': cost_price=%s, enabled=%s",
                name,
                cost_price,
                enabled,
            )
        except Exception as exc:
            log.exception("Failed to save item config")
            self._set_status(f"Error saving: {exc}", error=True)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _set_status(self, message: str, *, error: bool = False) -> None:
        color = (
            "#e05252"
            if error
            else ("#DCE4EE" if ctk.get_appearance_mode() == "Dark" else "#101010")
        )
        self._status_label.configure(text=message, text_color=color)
