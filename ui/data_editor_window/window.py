"""
The data editor window: a plain read/write/execute view of the underlying
records, no plotting. Hierarchy, as requested:

    COUNTRY -> YEAR / SCORE -> everything else
             (left_right/lib_auth)  (rubric id, summary, justification, sources)

Years within a country are listed chronologically (oldest first, like a
calendar/appointment list), not newest-first.

Read = the tree itself. Write = the editable fields in each year node.
Execute = the "Save" button, which hands the edited values to
..state.CompassState.save_entry() -- that's where they're actually
committed and written to disk. Only widget construction and reading
dpg values lives here; no data mutation or file I/O.

Runs two ways:
  - embedded in the main app, toggled by the "Data" button (see ui/app.py,
    which calls build() with the default standalone=False and later
    .toggle())
  - on its own, via the repo-root data_editor.py -> ui/data_editor_window/
    app.py, which calls build(standalone=True) so this window fills its
    own viewport immediately instead of starting hidden
"""

from __future__ import annotations

from typing import Callable

import dearpygui.dearpygui as dpg

from ..state import CompassState

WINDOW_TAG = "data_editor_window"
_BODY_TAG = f"{WINDOW_TAG}_body"


class DataEditorWindow:
    TAG_WINDOW = WINDOW_TAG

    def __init__(self, state: CompassState, on_data_changed: Callable[[], None]):
        self.state = state
        self.on_data_changed = on_data_changed
        self._search = ""
        self._visible = False

    # -- construction -----------------------------------------------------

    def build(self, *, standalone: bool = False) -> None:
        # embedded (default): a floating window, hidden until the "Data"
        # button toggles it. standalone: sized/positioned to fill its own
        # viewport and shown immediately -- see data_editor_window/app.py
        with dpg.window(tag=self.TAG_WINDOW, label="Data Editor",
                         width=-1 if standalone else 620, height=-1 if standalone else 680,
                         show=standalone, no_collapse=True,
                         no_move=standalone, no_resize=standalone, no_title_bar=standalone):
            dpg.add_text("Country -> Year/Score -> everything else. Edit fields, then Save to write them to disk.")
            dpg.add_input_text(hint="Filter countries...", callback=self._on_search, width=-1)
            dpg.add_separator()
            with dpg.child_window(tag=_BODY_TAG):
                pass

        if standalone:
            self._visible = True
            self._rebuild()

    def toggle(self) -> None:
        # tracked ourselves rather than queried back from dpg -- keeps this
        # independent of exactly when/how DPG's own item-shown state updates
        self._visible = not self._visible
        dpg.configure_item(self.TAG_WINDOW, show=self._visible)
        if self._visible:
            self._rebuild()

    # -- tree (the "read" side) ---------------------------------------------

    def _on_search(self, _sender, value: str) -> None:
        self._search = value.lower().strip()
        self._rebuild()

    def _rebuild(self) -> None:
        dpg.delete_item(_BODY_TAG, children_only=True)
        for country in sorted(self.state.countries, key=lambda c: c["name"]):
            if self._search and self._search not in country["name"].lower():
                continue
            self._build_country_node(country)

    def _build_country_node(self, country: dict) -> None:
        country_id = str(country["index"])
        years = self.state.scores.get(country_id, {})
        label = f"{country['name']} ({len(years)} year{'s' if len(years) != 1 else ''})"
        with dpg.tree_node(label=label, parent=_BODY_TAG):
            # chronological, oldest first -- like a calendar/appointment
            # list, not newest-on-top
            for year, score in sorted(years.items()):
                self._build_year_node(country_id, year, score)

            with dpg.group(horizontal=True):
                new_year_tag = dpg.add_input_text(width=90, hint="e.g. 2026")
                dpg.add_button(label="+ Add year",
                                callback=lambda s, a, u=new_year_tag: self._add_year(country_id, u))

    def _build_year_node(self, country_id: str, year: str, score: dict) -> None:
        rubric_id = score.get("rubric_id", "")
        eval_info = self.state.evaluations.get("evaluations", {}).get(rubric_id, {})
        just = eval_info.get("justification", {})

        header = f"{year} -- L/R {score.get('left_right', 0)}, Lib/Auth {score.get('lib_auth', 0)}"
        with dpg.tree_node(label=header):
            fields = {
                "left_right": dpg.add_slider_int(label="Left / Right", default_value=score.get("left_right", 0),
                                                  min_value=-100, max_value=100),
                "lib_auth": dpg.add_slider_int(label="Libertarian / Authoritarian",
                                                default_value=score.get("lib_auth", 0),
                                                min_value=-100, max_value=100),
                "rubric_id": dpg.add_input_text(label="Rubric ID", default_value=rubric_id),
                "summary": dpg.add_input_text(label="Summary", default_value=eval_info.get("summary", "")),
                "just_lr": dpg.add_input_text(label="Justification (L/R)", default_value=just.get("left_right", ""),
                                               multiline=True, height=50),
                "just_la": dpg.add_input_text(label="Justification (Lib/Auth)", default_value=just.get("lib_auth", ""),
                                               multiline=True, height=50),
                "sources": dpg.add_input_text(label="Sources (comma-separated)",
                                               default_value=", ".join(eval_info.get("sources", []))),
            }
            with dpg.group(horizontal=True):
                dpg.add_button(label="Save", callback=lambda s, a, u=(country_id, year, fields): self._save(*u))
                dpg.add_button(label="Delete", callback=lambda s, a, u=(country_id, year): self._delete(*u))
            dpg.add_separator()

    # -- actions: read dpg values, delegate the actual write to state ("execute") --

    def _save(self, country_id: str, year: str, fields: dict) -> None:
        sources = [s.strip() for s in dpg.get_value(fields["sources"]).split(",") if s.strip()]
        self.state.save_entry(
            country_id, year,
            left_right=dpg.get_value(fields["left_right"]),
            lib_auth=dpg.get_value(fields["lib_auth"]),
            rubric_id=dpg.get_value(fields["rubric_id"]).strip() or f"{country_id}-{year}",
            summary=dpg.get_value(fields["summary"]),
            justification_lr=dpg.get_value(fields["just_lr"]),
            justification_la=dpg.get_value(fields["just_la"]),
            sources=sources,
        )
        self.on_data_changed()
        self._rebuild()

    def _delete(self, country_id: str, year: str) -> None:
        self.state.delete_entry(country_id, year)
        self.on_data_changed()
        self._rebuild()

    def _add_year(self, country_id: str, year_input_tag: int) -> None:
        year = dpg.get_value(year_input_tag).strip()
        if not year:
            return
        self.state.add_year(country_id, year)
        self.on_data_changed()
        self._rebuild()
