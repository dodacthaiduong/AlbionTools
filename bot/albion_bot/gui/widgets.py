from __future__ import annotations

import io
import tkinter as tk
from tkinter import font as tkfont

import customtkinter as ctk
from PIL import Image, ImageTk


class SectionLabel(ctk.CTkLabel):
    """A bold section header label."""

    def __init__(self, parent: ctk.CTkFrame, text: str, **kwargs: object) -> None:
        super().__init__(
            parent,
            text=text,
            font=ctk.CTkFont(size=14, weight="bold"),
            **kwargs,
        )


class RegionPreview(ctk.CTkFrame):
    """A small thumbnail widget that displays a PNG screenshot of a captured region."""

    _THUMB_W = 120
    _THUMB_H = 60

    def __init__(self, parent: ctk.CTkFrame, **kwargs: object) -> None:
        super().__init__(parent, width=self._THUMB_W, height=self._THUMB_H, **kwargs)
        self.pack_propagate(False)

        # Use a plain tk.Label — avoids customtkinter rendering path that
        # can segfault on some Linux GPU drivers when scaling CTkImage.
        self._label = tk.Label(
            self,
            text="No preview",
            bg="#2b2b2b",
            fg="#888888",
            width=self._THUMB_W,
            height=self._THUMB_H,
        )
        self._label.pack(fill="both", expand=True)
        self._photo: ImageTk.PhotoImage | None = None

    def update_image(self, png_bytes: bytes) -> None:
        """Replace the thumbnail with a new image from raw PNG bytes."""
        img = Image.open(io.BytesIO(png_bytes))
        img.thumbnail((self._THUMB_W, self._THUMB_H), Image.Resampling.LANCZOS)
        self._photo = ImageTk.PhotoImage(img)
        self._label.configure(image=self._photo, text="")

    def clear(self) -> None:
        """Reset the preview back to the placeholder state."""
        self._photo = None
        self._label.configure(image="", text="No preview")


class LogBox(ctk.CTkFrame):
    """A scrollable, read-only text widget for status / log messages.

    Call :meth:`log` to append a line.  Call :meth:`clear` to wipe it.
    """

    def __init__(
        self, parent: ctk.CTkFrame, height: int = 120, **kwargs: object
    ) -> None:
        super().__init__(parent, **kwargs)

        mono = tkfont.Font(family="Courier", size=10)

        self._text = tk.Text(
            self,
            height=6,
            state="disabled",
            wrap="word",
            font=mono,
            bg="#1e1e1e",
            fg="#d4d4d4",
            insertbackground="#d4d4d4",
            relief="flat",
            borderwidth=0,
        )
        scrollbar = ctk.CTkScrollbar(self, command=self._text.yview)
        self._text.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        self._text.pack(side="left", fill="both", expand=True)

    def log(self, message: str) -> None:
        """Append *message* followed by a newline."""
        self._text.configure(state="normal")
        self._text.insert("end", message + "\n")
        self._text.see("end")
        self._text.configure(state="disabled")

    def clear(self) -> None:
        """Remove all text from the log box."""
        self._text.configure(state="normal")
        self._text.delete("1.0", "end")
        self._text.configure(state="disabled")
