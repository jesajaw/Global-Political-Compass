"""
Entry point wiring: identity + DPI first (before any window exists), then the main compass window.
Run via the repo-root main.py, not this file directly, so the "ui" package resolves correctly.
"""

import tkinter as tk

from . import style
from .compass_window import CompassWindow


def main() -> None:
    style.set_app_id()          # must come before Tk() -- see style.set_app_id
    root = tk.Tk()
    CompassWindow(root)
    root.mainloop()


def main_editor() -> None:
    """Just the Data window in its own root window (python data_editor.py)."""
    from .data_window import DataView

    style.set_app_id()
    root = tk.Tk()
    root.title("Global Political Compass -- Data")
    style.apply_style(root)
    style.set_window_icon(root)
    root.geometry(style.LAYOUT.data_window_size)
    root.minsize(style.px(1080), style.px(620))
    DataView(root, on_data_changed=lambda: None, padding=10).pack(fill="both", expand=True)
    root.mainloop()
