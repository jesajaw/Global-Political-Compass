"""
Standalone launcher for the data editor -- lets it run entirely on its own
(`python data_editor.py` from the repo root) as well as embedded inside the
main compass window via its "Data" button (see ui/app.py, which builds this
same DataEditorWindow with standalone=False and wires it to a toggle()).

Both launch paths share one CompassState and one DataEditorWindow class --
this file only adds the bit of dpg scaffolding (context/viewport/render
loop) an embedded window doesn't need for itself.
"""

from __future__ import annotations

from pathlib import Path

import dearpygui.dearpygui as dpg

from .. import theme
from ..state import CompassState
from .window import DataEditorWindow

TITLE = "Global Political Compass -- Data Editor"

# this file lives in ui/data_editor_window/, the data/ folder is two levels up
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


def main() -> None:
    theme.enable_dpi_awareness()

    state = CompassState(DATA_DIR)

    dpg.create_context()
    theme.apply_theme()
    theme.load_font()

    # no on_data_changed callback to wire here -- there's no compass window
    # in this process to refresh
    editor = DataEditorWindow(state, on_data_changed=lambda: None)
    editor.build(standalone=True)

    screen_w, screen_h = theme.get_screen_size()
    viewport_kwargs = dict(title=TITLE, width=round(screen_w * 0.5), height=round(screen_h * 0.75))
    icon_path = theme.get_icon_path()
    if icon_path:
        viewport_kwargs.update(small_icon=icon_path, large_icon=icon_path)
    dpg.create_viewport(**viewport_kwargs)
    dpg.setup_dearpygui()
    dpg.set_primary_window(editor.TAG_WINDOW, True)
    dpg.show_viewport()

    theme.enable_dark_titlebar(TITLE)
    theme.enable_taskbar_icon(TITLE, icon_path)

    while dpg.is_dearpygui_running():
        dpg.render_dearpygui_frame()

    dpg.destroy_context()


if __name__ == "__main__":
    main()
