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

        # slim control row below the canvas; packing it without fill keeps the cluster centered at any width.
        # Entry/Combobox size themselves by font metrics, not by a pixel height like Cell does, so
        # left to themselves they never quite match Cell's height. Each gets wrapped in its own
        # fixed-height frame (pack_propagate(False), same trick Cell itself uses) so all three
        # controls are exactly LAYOUT.control_height tall, no matter the platform's default widget size.
        row = ttk.Frame(frame)
        row.pack(pady=(10, 0))

        def _boxed(width: int) -> ttk.Frame:
            box = ttk.Frame(row, width=width, height=LAYOUT.control_height)
            box.pack_propagate(False)
            box.pack(side="left", padx=(0, 8))
            return box

        Cell(row, "Data", on_click=self._open_data, width=LAYOUT.data_button_width, height=LAYOUT.control_height) \
            .pack(side="left", padx=(0, 8))

        search_box = _boxed(style.px(LAYOUT.search_width_chars * 9))
        self.search = HintEntry(search_box, "Search country...", on_change=self.canvas.set_search)
        self.search.pack(fill="both", expand=True)

        year_box = _boxed(style.px(LAYOUT.combo_width_chars * 9 + 14))
        year_box.pack(padx=0)                        # last control in the row -- no trailing gap
        self.year_var = tk.StringVar()
        self.year_combo = ttk.Combobox(year_box, textvariable=self.year_var, state="readonly")
        self.year_combo.pack(fill="both", expand=True)
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
