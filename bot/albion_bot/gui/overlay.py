from __future__ import annotations

import tkinter as tk
from io import BytesIO

import mss
import mss.tools
from PIL import Image, ImageTk

from albion_bot.calibration.models import Rect


class SelectionOverlay:
    """Fullscreen drag-to-select overlay.

    Takes a screenshot of the current screen, displays it frozen as the
    background, then lets the user drag a red rectangle over it.

    Usage::

        overlay = SelectionOverlay()
        region = overlay.ask_region(parent_widget)
        # region is a Rect or None if the user pressed Escape
    """

    def ask_region(self, parent: tk.Misc) -> Rect | None:
        """Show the overlay and block until the user selects a region.

        Returns a :class:`Rect` with absolute screen coordinates, or ``None``
        if the user pressed *Escape*.
        """
        self._result: Rect | None = None

        screen_w = parent.winfo_screenwidth()
        screen_h = parent.winfo_screenheight()

        # --- take a screenshot before opening the overlay -------------------
        with mss.mss() as sct:
            monitor = {"left": 0, "top": 0, "width": screen_w, "height": screen_h}
            raw = sct.grab(monitor)
            png_bytes = mss.tools.to_png(raw.rgb, raw.size)

        img = Image.open(BytesIO(png_bytes)).convert("RGBA")
        # Darken slightly so the selection rectangle stands out
        overlay_img = Image.new("RGBA", img.size, (0, 0, 0, 80))
        img = Image.alpha_composite(img, overlay_img).convert("RGB")
        photo = ImageTk.PhotoImage(img)

        # --- toplevel setup -------------------------------------------------
        top = tk.Toplevel(parent)
        top.attributes("-fullscreen", True)
        top.attributes("-topmost", True)
        top.overrideredirect(True)
        top.geometry(f"{screen_w}x{screen_h}+0+0")

        # --- canvas with screenshot background ------------------------------
        canvas = tk.Canvas(
            top,
            width=screen_w,
            height=screen_h,
            cursor="crosshair",
            highlightthickness=0,
            bd=0,
        )
        canvas.pack(fill="both", expand=True)
        canvas.create_image(0, 0, anchor="nw", image=photo)

        # hint text
        canvas.create_text(
            screen_w // 2,
            30,
            text="Drag to select region  •  Esc to cancel",
            fill="white",
            font=("Arial", 14, "bold"),
        )

        # keep reference so GC doesn't collect the photo
        canvas._photo = photo  # type: ignore[attr-defined]

        # State shared across callbacks
        _state: dict = {"start_x": 0, "start_y": 0, "rect_id": None, "label_id": None}

        # --- event handlers -------------------------------------------------
        def on_press(event: tk.Event) -> None:
            _state["start_x"] = event.x
            _state["start_y"] = event.y
            if _state["rect_id"] is not None:
                canvas.delete(_state["rect_id"])
            if _state["label_id"] is not None:
                canvas.delete(_state["label_id"])
            _state["rect_id"] = canvas.create_rectangle(
                event.x,
                event.y,
                event.x,
                event.y,
                outline="red",
                width=2,
            )

        def on_drag(event: tk.Event) -> None:
            if _state["rect_id"] is not None:
                canvas.coords(
                    _state["rect_id"],
                    _state["start_x"],
                    _state["start_y"],
                    event.x,
                    event.y,
                )
            # show live size label
            w = abs(event.x - _state["start_x"])
            h = abs(event.y - _state["start_y"])
            if _state["label_id"] is not None:
                canvas.delete(_state["label_id"])
            _state["label_id"] = canvas.create_text(
                event.x + 8,
                event.y + 8,
                text=f"{w}×{h}",
                fill="yellow",
                font=("Arial", 11),
                anchor="nw",
            )

        def on_release(event: tk.Event) -> None:
            x1 = min(_state["start_x"], event.x)
            y1 = min(_state["start_y"], event.y)
            x2 = max(_state["start_x"], event.x)
            y2 = max(_state["start_y"], event.y)
            w = x2 - x1
            h = y2 - y1
            if w > 2 and h > 2:
                self._result = Rect(x=x1, y=y1, w=w, h=h)
            top.destroy()

        def on_escape(event: tk.Event) -> None:  # noqa: ARG001
            self._result = None
            top.destroy()

        canvas.bind("<ButtonPress-1>", on_press)
        canvas.bind("<B1-Motion>", on_drag)
        canvas.bind("<ButtonRelease-1>", on_release)
        top.bind("<Escape>", on_escape)

        # Block until the overlay window is closed
        parent.wait_window(top)

        return self._result
