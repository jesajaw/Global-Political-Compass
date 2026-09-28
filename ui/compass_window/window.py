"""
The main compass window: a bordered canvas that fills almost the entire window, and a slim centered
control row (Data tile / search / year) pinned below it -- same layout as before, now in tkinter.

This window only wires things together: the drawing is view.CompassCanvas, the numbers come from
data.scoring (via the canvas), the colours/sizes from ..style. It also owns the Data window (one
instance at a time) and refreshes itself whenever that window changes something.
"""

import tkinter as tk
from tkinter import ttk

from data import store
from .. import style
from ..style import LAYOUT
from ..widgets import Cell, HintEntry
from . import view

WINDOW_TITLE = "Global Political Compass Engine"
SCREEN_FRACTION = 0.8


class CompassWindow:
    TITLE = WINDOW_TITLE

    def __init__(self, root: tk.Tk):
        self.root = root
        self._data_window = None

        root.title(self.TITLE)
        style.apply_style(root)
        style.set_window_icon(root)
        self._size_and_center(root)
        root.minsize(style.px(640), style.px(480))

        self._build()
        self._refresh_years()

    # -- construction -------------------------------------------------------------------

    def _size_and_center(self, root) -> None:
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        w, h = round(sw * SCREEN_FRACTION), round(sh * SCREEN_FRACTION)
        root.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

    def _build(self) -> None:
        frame = ttk.Frame(self.root, padding=12)
        frame.pack(fill="both", expand=True)

        self.canvas = view.CompassCanvas(frame)
        self.canvas.pack(fill="both", expand=True)

        # slim control row below the canvas; packing it without fill keeps the cluster centered at any width
        row = ttk.Frame(frame)
        row.pack(pady=(10, 0))

        Cell(row, "Data", on_click=self._open_data, width=LAYOUT.data_button_width, height=LAYOUT.control_height) \
            .pack(side="left", padx=(0, 8))

        self.search = HintEntry(row, "Search country...", on_change=self.canvas.set_search, width=LAYOUT.search_width_chars)
        self.search.pack(side="left", padx=(0, 8), ipady=6)

        self.year_var = tk.StringVar()
        self.year_combo = ttk.Combobox(row, textvariable=self.year_var, state="readonly", width=LAYOUT.combo_width_chars)
        self.year_combo.pack(side="left", ipady=4)
        self.year_combo.bind("<<ComboboxSelected>>", lambda _e: self.canvas.set_year(self.year_var.get()))

    # -- data window ----------------------------------------------------------------------

    def _open_data(self) -> None:
        from ..data_window import DataWindow    # imported here: it pulls in the agent, no need to load it before it's needed

        if self._data_window is not None and self._data_window.winfo_exists():
            self._data_window.deiconify()
            self._data_window.lift()
            self._data_window.focus_force()
            return
        self._data_window = DataWindow(self.root, on_data_changed=self.refresh)

    # -- state ----------------------------------------------------------------------------------

    def _refresh_years(self) -> None:
        years = store.all_years()
        self.year_combo.configure(values=years)
        if self.year_var.get() not in years:
            self.year_var.set(years[0] if years else "")     # newest year, or blank if there's no data at all
        self.year_combo.configure(state="readonly" if years else "disabled")
        self.canvas.set_year(self.year_var.get())

    def refresh(self) -> None:
        """Called by the Data window after it added/edited/deleted an entry."""
        self._refresh_years()
