"""
Global Political Compass -- app shell: builds the window (search box, year
picker, compass canvas) and drives the render loop.

Only the UI lives here. Loading real countries/scores from the web and
evaluating them is scripts/agent.py's job (not built out yet) -- this reads
whatever agent.py has already written to data/*.json, and falls back to
demo_data.py if those files don't exist yet, so the UI works on its own
before the pipeline does.
"""

from __future__ import annotations

import json
from pathlib import Path

import dearpygui.dearpygui as dpg

import theme
import compass_view
from demo_data import DEFAULT_COUNTRIES, DEFAULT_SCORES, DEFAULT_EVALUATIONS

WINDOW_TITLE = "Global Political Compass Engine"
DRAWLIST_TAG = "compass_drawlist"
PRIMARY_WINDOW_TAG = "primary_window"

# this file lives in ui/, the data/ folder is one level up at the repo root
DATA_DIR = Path(__file__).resolve().parent.parent / "data"


class PoliticalCompassApp:
    def __init__(self) -> None:
        self.countries = DEFAULT_COUNTRIES
        self.scores = DEFAULT_SCORES
        self.evaluations = DEFAULT_EVALUATIONS

        self.selected_year = "2024"
        self.search_query = ""

        self._load_data()

    def _load_data(self) -> None:
        # Overlays data/*.json onto the demo data if present. Still just a
        # file read -- the actual fetch+evaluate pipeline is scripts/agent.py.
        for attr, filename in (
            ("countries", "countries.json"),
            ("scores", "country_scores.json"),
            ("evaluations", "evaluations.json"),
        ):
            path = DATA_DIR / filename
            if not path.exists():
                continue
            try:
                setattr(self, attr, json.loads(path.read_text(encoding="utf-8")))
            except Exception as e:
                print(f"Could not load {filename} ({e}), keeping placeholder data.")

        years = {y for country_scores in self.scores.values() for y in country_scores}
        self.available_years = sorted(years, reverse=True) or ["2024"]
        self.selected_year = self.available_years[0]

    # -- UI callbacks ------------------------------------------------------

    def _on_search(self, _sender, value: str) -> None:
        self.search_query = value.lower().strip()

    def _on_year_change(self, _sender, value: str) -> None:
        self.selected_year = value

    def _on_viewport_resize(self) -> None:
        # Keeps the compass canvas filling the window instead of staying
        # pinned at its initial 820x720, so resizing the window actually
        # does something.
        w = dpg.get_viewport_client_width() - 2 * theme.LAYOUT.padding
        h = dpg.get_viewport_client_height() - theme.LAYOUT.header_height - 2 * theme.LAYOUT.padding
        dpg.configure_item(
            DRAWLIST_TAG,
            width=max(w, theme.LAYOUT.canvas_min),
            height=max(h, theme.LAYOUT.canvas_min),
        )

    # -- UI construction -----------------------------------------------------

    def _build_ui(self) -> None:
        with dpg.window(tag=PRIMARY_WINDOW_TAG, label=WINDOW_TITLE):
            # a stretch/fixed table keeps the search box + year picker
            # pinned to the right edge at any window width, instead of the
            # fixed-pixel spacer that only looked right at one size
            with dpg.table(header_row=False, borders_innerV=False, borders_outerV=False,
                            borders_innerH=False, borders_outerH=False):
                dpg.add_table_column(init_width_or_weight=3)
                dpg.add_table_column(width_fixed=True, init_width_or_weight=310)
                with dpg.table_row():
                    dpg.add_text(WINDOW_TITLE)
                    with dpg.group(horizontal=True):
                        dpg.add_input_text(hint="Search country...", width=200, callback=self._on_search)
                        dpg.add_combo(items=self.available_years, default_value=self.selected_year,
                                      width=90, callback=self._on_year_change)

            dpg.add_spacer(height=8)

            with dpg.drawlist(tag=DRAWLIST_TAG, width=820, height=720):
                pass

    def _render_frame(self) -> None:
        compass_view.draw_compass(
            DRAWLIST_TAG, self.countries, self.scores, self.evaluations,
            self.selected_year, self.search_query,
        )

    # -- lifecycle -----------------------------------------------------------

    def run(self) -> None:
        dpg.create_context()
        theme.apply_theme()
        theme.load_font()

        self._build_ui()

        dpg.create_viewport(title=WINDOW_TITLE, width=880, height=820, resizable=True)
        dpg.set_viewport_resize_callback(lambda: self._on_viewport_resize())
        dpg.setup_dearpygui()
        dpg.set_primary_window(PRIMARY_WINDOW_TAG, True)
        dpg.show_viewport()

        theme.enable_dark_titlebar(WINDOW_TITLE)

        while dpg.is_dearpygui_running():
            self._render_frame()
            dpg.render_dearpygui_frame()

        dpg.destroy_context()


if __name__ == "__main__":
    theme.enable_dpi_awareness()
    PoliticalCompassApp().run()
