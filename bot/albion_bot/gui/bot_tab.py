from __future__ import annotations

import logging
import threading
from typing import Any

import customtkinter as ctk

from albion_bot.db.connection import get_db
from albion_bot.gui.widgets import LogBox, SectionLabel
from albion_bot.selling.loop import run_sell_loop

log = logging.getLogger(__name__)


class _LogBoxHandler(logging.Handler):
    """Forwards log records to a LogBox widget, safely scheduling via tkinter's event loop."""

    def __init__(self, log_box: LogBox) -> None:
        super().__init__()
        self._log_box = log_box
        self.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            # Schedule the append on the main thread via tkinter's after mechanism
            self._log_box.after(0, self._log_box.log, msg)
        except Exception:
            self.handleError(record)


class BotTab:
    """Bot control tab — start/stop the sell loop and monitor session stats."""

    def __init__(self, parent: ctk.CTkFrame) -> None:
        self._parent = parent

        self._stop_flag: list[bool] = [False]
        self._bot_thread: threading.Thread | None = None
        self._log_handler: _LogBoxHandler | None = None

        self._build_ui()
        self._load_profiles()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self._parent.grid_columnconfigure(0, weight=1)
        self._parent.grid_rowconfigure(2, weight=1)  # log section expands

        # ── Bot Control section ────────────────────────────────────────
        control_frame = ctk.CTkFrame(self._parent)
        control_frame.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 6))
        control_frame.grid_columnconfigure(1, weight=1)

        SectionLabel(control_frame, text="Bot Control").grid(
            row=0, column=0, columnspan=4, sticky="w", padx=10, pady=(8, 4)
        )

        # Profile selector row
        ctk.CTkLabel(control_frame, text="Profile:").grid(
            row=1, column=0, padx=(10, 6), pady=6, sticky="w"
        )

        self._profile_var = ctk.StringVar(value="")
        self._profile_menu = ctk.CTkOptionMenu(
            control_frame, variable=self._profile_var, values=["—"], width=180
        )
        self._profile_menu.grid(row=1, column=1, padx=(0, 8), pady=6, sticky="w")

        self._refresh_profiles_btn = ctk.CTkButton(
            control_frame,
            text="Refresh profiles",
            width=120,
            command=self._load_profiles,
        )
        self._refresh_profiles_btn.grid(row=1, column=2, padx=(0, 10), pady=6)

        # Start / Stop buttons
        btn_frame = ctk.CTkFrame(control_frame, fg_color="transparent")
        btn_frame.grid(row=2, column=0, columnspan=4, padx=10, pady=(4, 8), sticky="w")

        self._start_btn = ctk.CTkButton(
            btn_frame,
            text="Start Bot",
            width=110,
            fg_color="#2e7d32",
            hover_color="#1b5e20",
            command=self._start_bot,
        )
        self._start_btn.pack(side="left", padx=(0, 10))

        self._stop_btn = ctk.CTkButton(
            btn_frame,
            text="Stop Bot",
            width=110,
            fg_color="#c62828",
            hover_color="#8e0000",
            state="disabled",
            command=self._stop_bot,
        )
        self._stop_btn.pack(side="left", padx=(0, 16))

        self._status_label = ctk.CTkLabel(
            btn_frame,
            text="Idle",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#9e9e9e",
        )
        self._status_label.pack(side="left")

        # ── Session Stats section ──────────────────────────────────────
        stats_frame = ctk.CTkFrame(self._parent)
        stats_frame.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 6))
        stats_frame.grid_columnconfigure((1, 3), weight=1)

        SectionLabel(stats_frame, text="Session Stats").grid(
            row=0, column=0, columnspan=4, sticky="w", padx=10, pady=(8, 4)
        )

        stat_defs = [
            ("Cycles completed:", "_cycles_label"),
            ("Items sold:", "_items_label"),
            ("Total revenue:", "_revenue_label"),
            ("Errors:", "_errors_label"),
        ]

        for i, (caption, attr) in enumerate(stat_defs):
            row_idx = 1 + i // 2
            col_base = (i % 2) * 2

            ctk.CTkLabel(stats_frame, text=caption, anchor="w").grid(
                row=row_idx,
                column=col_base,
                padx=(10 if col_base == 0 else 20, 4),
                pady=4,
                sticky="w",
            )
            value_label = ctk.CTkLabel(
                stats_frame,
                text="0",
                anchor="w",
                font=ctk.CTkFont(size=13, weight="bold"),
            )
            value_label.grid(
                row=row_idx, column=col_base + 1, padx=(0, 10), pady=4, sticky="w"
            )
            setattr(self, attr, value_label)

        # bottom padding row
        stats_frame.grid_rowconfigure(3, minsize=6)

        # ── Log section ────────────────────────────────────────────────
        log_frame = ctk.CTkFrame(self._parent)
        log_frame.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 10))
        log_frame.grid_rowconfigure(1, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)

        log_header = ctk.CTkFrame(log_frame, fg_color="transparent")
        log_header.grid(row=0, column=0, sticky="ew", padx=10, pady=(8, 2))

        SectionLabel(log_header, text="Log").pack(side="left")

        self._clear_log_btn = ctk.CTkButton(
            log_header, text="Clear", width=60, command=self._clear_log
        )
        self._clear_log_btn.pack(side="right")

        self._log_box = LogBox(log_frame, height=200)
        self._log_box.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

    # ------------------------------------------------------------------
    # Profile loading
    # ------------------------------------------------------------------

    def _load_profiles(self) -> None:
        self._refresh_profiles_btn.configure(state="disabled")
        try:
            db = get_db()
            profiles = [
                doc["profile_name"]
                for doc in db.calibrations.find({}, {"profile_name": 1})
            ]
        except Exception as exc:
            log.exception("Failed to load calibration profiles")
            self._log_box.log(f"[ERROR] Could not load profiles: {exc}")
            self._refresh_profiles_btn.configure(state="normal")
            return

        if profiles:
            self._profile_menu.configure(values=profiles)
            self._profile_var.set(profiles[0])
        else:
            self._profile_menu.configure(values=["—"])
            self._profile_var.set("—")
            self._log_box.log("[WARN] No calibration profiles found in MongoDB.")

        self._refresh_profiles_btn.configure(state="normal")

    # ------------------------------------------------------------------
    # Bot start / stop
    # ------------------------------------------------------------------

    def _start_bot(self) -> None:
        profile = self._profile_var.get()
        if not profile or profile == "—":
            self._log_box.log(
                "[ERROR] Select a valid calibration profile before starting."
            )
            return

        self._stop_flag = [False]

        # Attach log handler
        self._log_handler = _LogBoxHandler(self._log_box)
        logging.getLogger().addHandler(self._log_handler)

        # Reset stats display
        self._reset_stats()

        # Update UI state
        self._start_btn.configure(state="disabled")
        self._stop_btn.configure(state="normal")
        self._set_status("Running", color="#66bb6a")
        self._log_box.log(f"[INFO] Starting bot with profile '{profile}'…")

        # Launch thread
        self._bot_thread = threading.Thread(
            target=self._run_bot,
            args=(profile,),
            daemon=True,
            name="sell-loop",
        )
        self._bot_thread.start()

        # Begin periodic stats refresh
        self._schedule_stats_refresh()

    def _stop_bot(self) -> None:
        self._stop_flag[0] = True
        self._stop_btn.configure(state="disabled")
        self._set_status("Stopping…", color="#ffa726")
        self._log_box.log("[INFO] Stop requested — finishing current cycle…")

    def _run_bot(self, profile: str) -> None:
        """Runs in the sell-loop thread. Calls back to the main thread when done."""
        try:
            run_sell_loop(profile=profile, stop_flag=self._stop_flag)
        except Exception as exc:
            # Schedule error display on main thread
            self._parent.after(0, self._log_box.log, f"[ERROR] Bot crashed: {exc}")
        finally:
            self._parent.after(0, self._on_bot_finished)

    def _on_bot_finished(self) -> None:
        """Called on the main thread after the sell loop exits."""
        # Remove log handler
        if self._log_handler is not None:
            logging.getLogger().removeHandler(self._log_handler)
            self._log_handler = None

        self._start_btn.configure(state="normal")
        self._stop_btn.configure(state="disabled")
        self._set_status("Idle", color="#9e9e9e")
        self._log_box.log("[INFO] Bot stopped.")

    # ------------------------------------------------------------------
    # Periodic stats refresh
    # ------------------------------------------------------------------

    def _schedule_stats_refresh(self) -> None:
        self._parent.after(2000, self._refresh_stats)

    def _refresh_stats(self) -> None:
        """Fetch the latest session stats from MongoDB and update labels."""
        # Only keep refreshing while the thread is alive
        if self._bot_thread is None or not self._bot_thread.is_alive():
            return

        try:
            db = get_db()
            session = db.bot_sessions.find_one(
                {"status": "running"}, sort=[("started_at", -1)]
            )
            if session:
                stats = session.get("stats", {})
                self._cycles_label.configure(text=str(stats.get("cycles_completed", 0)))
                self._items_label.configure(text=str(stats.get("items_sold", 0)))
                revenue = stats.get("total_revenue", 0)
                self._revenue_label.configure(text=f"{revenue:,}")
                self._errors_label.configure(text=str(stats.get("errors_count", 0)))
        except Exception as exc:
            log.debug("Stats refresh error: %s", exc)

        # Reschedule
        self._schedule_stats_refresh()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _reset_stats(self) -> None:
        for attr in (
            "_cycles_label",
            "_items_label",
            "_revenue_label",
            "_errors_label",
        ):
            getattr(self, attr).configure(text="0")

    def _clear_log(self) -> None:
        self._log_box.clear()

    def _set_status(self, text: str, color: str = "#9e9e9e") -> None:
        self._status_label.configure(text=text, text_color=color)
