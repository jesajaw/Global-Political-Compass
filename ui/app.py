"""
Orchestrator -- creates the DPG context, applies the shared theme, loads
state, builds the two windows, and drives the render loop.

No dpg.add_* widget calls live here (the create_context/create_viewport/
setup_dearpygui/show_viewport calls are DPG framework setup, not widgets).
Each window's own package owns its widgets:
  - compass_window/window.py  -> the main compass window
  - data_editor_window/window.py -> the CRUD data editor

Run via the repo-root main.py, not this file directly, so the "ui" package
resolves correctly.
"""

from __future__ import annotations

from pathlib import Path

import dearpygui.dearpygui as dpg

from . import theme
from .state import CompassState
from .compass_window import CompassWindow
from .data_editor_window import DataEditorWindow

# this file lives in ui/, the data/ folder is one level up at the repo root
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
VIEWPORT_SCREEN_FRACTION = 0.8


def main() -> None:
    theme.enable_dpi_awareness()

    state = CompassState(DATA_DIR)

    dpg.create_context()
    theme.apply_theme()
    theme.load_font()

    # each window only needs a callback into the other, not a direct
    # reference -- the late-binding closures below resolve fine once both
    # objects exist, since neither callback fires until well after this
    compass = CompassWindow(state, on_open_editor=lambda: editor.toggle())
    editor = DataEditorWindow(state, on_data_changed=lambda: compass.refresh_year_combo())

    compass.build()
    editor.build()

    screen_w, screen_h = theme.get_screen_size()
    viewport_kwargs = dict(
        title=CompassWindow.TITLE,
        width=round(screen_w * VIEWPORT_SCREEN_FRACTION),
        height=round(screen_h * VIEWPORT_SCREEN_FRACTION),
        resizable=True,
    )
    icon_path = theme.get_icon_path()
    if icon_path:
        viewport_kwargs.update(small_icon=icon_path, large_icon=icon_path)
    dpg.create_viewport(**viewport_kwargs)
    dpg.set_viewport_resize_callback(lambda: compass.on_viewport_resize())
    dpg.setup_dearpygui()
    dpg.set_primary_window(compass.TAG_WINDOW, True)
    dpg.show_viewport()
    compass.on_viewport_resize()  # size the canvas to the 80%-screen viewport immediately

    theme.enable_dark_titlebar(CompassWindow.TITLE)

    while dpg.is_dearpygui_running():
        compass.render_frame()
        dpg.render_dearpygui_frame()

    dpg.destroy_context()
