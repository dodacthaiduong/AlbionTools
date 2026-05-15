from __future__ import annotations

import customtkinter as ctk

from albion_bot.gui.bot_tab import BotTab
from albion_bot.gui.calibration_tab import CalibrationTab
from albion_bot.gui.config_tab import ConfigTab

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class App(ctk.CTk):
    """Main application window for Albion Auto-Seller."""

    def __init__(self) -> None:
        super().__init__()

        self.title("Albion Auto-Seller")
        self.geometry("1000x700")
        self.resizable(False, False)

        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        # Main layout: tabview fills the top, status bar sits at the bottom
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        self.grid_columnconfigure(0, weight=1)

        # Tab view
        self._tabview = ctk.CTkTabview(self)
        self._tabview.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10, 0))

        for name in ("Calibration", "Config", "Bot"):
            self._tabview.add(name)

        # Instantiate tab controllers, passing the tab frame as parent
        CalibrationTab(self._tabview.tab("Calibration"))
        ConfigTab(self._tabview.tab("Config"))
        BotTab(self._tabview.tab("Bot"))

        # Status bar
        status_frame = ctk.CTkFrame(self, height=30, corner_radius=0)
        status_frame.grid(row=1, column=0, sticky="ew", padx=0, pady=(4, 0))
        status_frame.grid_columnconfigure(0, weight=1)

        self._status_label = ctk.CTkLabel(
            status_frame,
            text="Ready",
            anchor="w",
            padx=8,
        )
        self._status_label.grid(row=0, column=0, sticky="ew")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_status(self, msg: str) -> None:
        """Update the status bar message."""
        self._status_label.configure(text=msg)


def launch() -> None:
    """Create and run the application."""
    app = App()
    app.mainloop()
