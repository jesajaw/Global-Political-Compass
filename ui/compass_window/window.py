"""
The main compass window: a bordered canvas "cell" that fills almost the
entire window, and a slim centered control row (search / year / "Data"
button) pinned below it.

All widget construction and DPG callbacks for this window live here --
drawing the actual compass is view.py's CompassCanvas, shared app state is
..state, all colors/sizes come from ..theme. Nothing here is built or
styled ad hoc, and this window never draws directly -- it just wires
current state into canvas.render() once per frame.

No zoom/pan: the default 80%-of-screen view is the only view (see
theme.LAYOUT's bigger point/text sizes). CompassCanvas only pays for an
actual redraw when something that affects the picture changed since last
frame -- recreating every draw item unconditionally at the render loop's
full rate was the actual source of the visible flicker/jank.
"""

from __future__ import annotations

from typing import Callable

import dearpygui.dearpygui as dpg

from .. import theme
from ..state import CompassState
from . import view

WINDOW_TITLE = "Global Political Compass Engine"


class CompassWindow:
    TITLE = WINDOW_TITLE

    TAG_WINDOW = "primary_window"
    TAG_CANVAS_FRAME = "compass_canvas_frame"
    TAG_DRAWLIST = "compass_drawlist"
    TAG_YEAR_COMBO = "year_combo"
    TAG_EDITOR_BUTTON = "editor_toggle_button"

    def __init__(self, state: CompassState, on_open_editor: Callable[[], None]):
        self.state = state
        self.on_open_editor = on_open_editor
        # owns compute/hit-test/draw + the "did anything change" cache for
        # the canvas -- this window only calls .render() once per frame
        self.canvas = view.CompassCanvas(self.TAG_DRAWLIST)

    # -- construction -----------------------------------------------------

    def build(self) -> None:
        with dpg.window(tag=self.TAG_WINDOW, label=self.TITLE):
            # a bordered "cell" that fills almost the entire window -- only
            # the control row below it is reserved space. The drawlist
            # sits inset a little inside it so the plot has room to be
            # readable instead of floating in a window that's mostly empty
            # margin around a small canvas.
            with dpg.child_window(tag=self.TAG_CANVAS_FRAME, border=True):
                with dpg.drawlist(tag=self.TAG_DRAWLIST, width=820, height=720):
                    pass

            dpg.add_spacer(height=8)

            # a slim control row below the cell. A 3-column table with
            # equal-weight spacer columns either side of a fixed-width
            # middle column keeps the whole cluster centered at any window
            # width, and the controls sit in one horizontal group so they
            # read as a single row of "keys" next to each other. Only the
            # "Data" button lives here now -- there's nothing left for a
            # separate "Load" button to do, since editing (via the data
            # editor) writes straight into the same in-memory state this
            # window already reads from.
            control_width = theme.LAYOUT.data_button_w + theme.LAYOUT.search_width + theme.LAYOUT.combo_width + 20
            with dpg.table(header_row=False, borders_innerV=False, borders_outerV=False,
                            borders_innerH=False, borders_outerH=False):
                dpg.add_table_column(init_width_or_weight=1)
                dpg.add_table_column(width_fixed=True, init_width_or_weight=control_width)
                dpg.add_table_column(init_width_or_weight=1)
                with dpg.table_row():
                    dpg.add_spacer()
                    with dpg.group(horizontal=True):
                        # plain text label, not an icon glyph: DPG's
                        # default/fallback font has no symbol codepoints
                        # (e.g. the U+2699 gear used before rendered as a
                        # tofu/placeholder box)
                        dpg.add_button(tag=self.TAG_EDITOR_BUTTON, label="Data",
                                        width=theme.LAYOUT.data_button_w, height=theme.LAYOUT.data_button_h,
                                        callback=lambda: self.on_open_editor())
                        dpg.add_input_text(hint="Search country...", width=theme.LAYOUT.search_width,
                                            callback=self._on_search)
                        dpg.add_combo(tag=self.TAG_YEAR_COMBO, items=self.state.available_years,
                                      default_value=self.state.selected_year, width=theme.LAYOUT.combo_width,
                                      callback=self._on_year_change)
                    dpg.add_spacer()

    # -- callbacks ----------------------------------------------------------

    def _on_search(self, _sender, value: str) -> None:
        self.state.search_query = value.lower().strip()

    def _on_year_change(self, _sender, value: str) -> None:
        self.state.selected_year = value

    # -- layout ---------------------------------------------------------------

    def on_viewport_resize(self) -> None:
        # the cell fills the whole window except the control row below it
        # and a little margin -- keeps it filling the window as it resizes
        # instead of staying pinned at its initial size
        w = dpg.get_viewport_client_width() - 2 * theme.LAYOUT.padding
        h = dpg.get_viewport_client_height() - theme.LAYOUT.control_bar_height - 2 * theme.LAYOUT.padding
        frame_w = max(w, theme.LAYOUT.canvas_min)
        frame_h = max(h, theme.LAYOUT.canvas_min)
        dpg.configure_item(self.TAG_CANVAS_FRAME, width=frame_w, height=frame_h)

        inset = 2 * theme.LAYOUT.window_padding
        dpg.configure_item(self.TAG_DRAWLIST, width=max(frame_w - inset, theme.LAYOUT.canvas_min // 2),
                            height=max(frame_h - inset, theme.LAYOUT.canvas_min // 2))

    def refresh_year_combo(self) -> None:
        # called by the data editor after it adds/removes a year entry
        if dpg.does_item_exist(self.TAG_YEAR_COMBO):
            dpg.configure_item(self.TAG_YEAR_COMBO, items=self.state.available_years,
                                default_value=self.state.selected_year)

    # -- render loop --------------------------------------------------------

    def render_frame(self) -> None:
        # all compute/hit-test/draw + the "did anything change" cache lives
        # in view.CompassCanvas now -- this is just wiring current state in
        self.canvas.render(
            self.state.countries, self.state.scores, self.state.evaluations,
            self.state.selected_year, self.state.search_query,
        )
