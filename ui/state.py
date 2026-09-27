"""
Shared application state: the in-memory countries/scores/evaluations, the
current view state (selected year, search query), and the load/save logic
for data/*.json.

Neither window owns this -- compass_window reads it to draw and mutates the
view state (search/year); data_editor_window reads and writes the records
themselves through save_entry/delete_entry/add_year, which also handle
persisting to disk. No dpg calls and no widgets live here.
"""

from __future__ import annotations

import json
from pathlib import Path

from .demo_data import DEFAULT_COUNTRIES, DEFAULT_SCORES, DEFAULT_EVALUATIONS


class CompassState:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir

        self.countries = DEFAULT_COUNTRIES
        self.scores = DEFAULT_SCORES
        self.evaluations = DEFAULT_EVALUATIONS

        self.selected_year = "2024"
        self.search_query = ""
        self.available_years = ["2024"]

        self._load_data()

    # -- loading ----------------------------------------------------------

    def _load_data(self) -> None:
        # Overlays data/*.json onto the demo data if present. Just a file
        # read -- the actual fetch+evaluate pipeline is scripts/agent.py.
        for attr, filename in (
            ("countries", "countries.json"),
            ("scores", "country_scores.json"),
            ("evaluations", "evaluations.json"),
        ):
            path = self.data_dir / filename
            if not path.exists():
                continue
            try:
                setattr(self, attr, json.loads(path.read_text(encoding="utf-8")))
            except Exception as e:
                print(f"Could not load {filename} ({e}), keeping placeholder data.")

        self.refresh_years()

    def reload(self) -> None:
        # Public re-read of data/*.json, for the header's "Load" button --
        # picks up edits made outside the app (by scripts/agent.py, or by
        # hand) without needing to restart.
        self._load_data()

    def refresh_years(self) -> None:
        years = {y for country_scores in self.scores.values() for y in country_scores}
        self.available_years = sorted(years, reverse=True) or ["2024"]
        if self.selected_year not in self.available_years:
            self.selected_year = self.available_years[0]

    # -- persistence (the data editor's "execute" step) ------------------------

    def _persist(self) -> None:
        try:
            (self.data_dir / "country_scores.json").write_text(
                json.dumps(self.scores, indent=2, ensure_ascii=False), encoding="utf-8")
            (self.data_dir / "evaluations.json").write_text(
                json.dumps(self.evaluations, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            print(f"Could not save data ({e}).")

    def save_entry(
        self, country_id: str, year: str, *,
        left_right: int, lib_auth: int, rubric_id: str,
        summary: str, justification_lr: str, justification_la: str, sources: list[str],
    ) -> None:
        self.scores.setdefault(country_id, {})[year] = {
            "left_right": left_right, "lib_auth": lib_auth, "rubric_id": rubric_id,
        }
        self.evaluations.setdefault("evaluations", {})[rubric_id] = {
            "summary": summary,
            "justification": {"left_right": justification_lr, "lib_auth": justification_la},
            "sources": sources,
        }
        self._persist()
        self.refresh_years()

    def delete_entry(self, country_id: str, year: str) -> None:
        rubric_id = self.scores.get(country_id, {}).get(year, {}).get("rubric_id")
        self.scores.get(country_id, {}).pop(year, None)
        if rubric_id:
            self.evaluations.get("evaluations", {}).pop(rubric_id, None)
        self._persist()
        self.refresh_years()

    def add_year(self, country_id: str, year: str) -> None:
        self.scores.setdefault(country_id, {})[year] = {
            "left_right": 0, "lib_auth": 0, "rubric_id": f"{country_id}-{year}",
        }
        self._persist()
        self.refresh_years()
