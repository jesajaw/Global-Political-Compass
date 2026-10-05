"""
Drop-in replacement for store.py that keeps everything in ONE SQLite file (data/compass.db)
instead of one JSON file per country. Same public functions, same behaviour -- ui/, agent/ and
scoring.py don't notice the difference. That is the point of the exercise.

    Switch:      rename store.py -> store_json.py, then store_sqlite.py -> store.py
    Import JSON: python -m data.store_sqlite --import-json     (copies data/countries/*.json into the db)

What SQL gives you that JSON files don't: the database does the searching. get_scores() below
is one GROUP BY query instead of a Python loop over every country -- see average_scores().
"""

from __future__ import annotations

import json
import re
import sqlite3
import sys
from datetime import date
from pathlib import Path

from .categories import axes_from_categories
from .models import CategoryRating, Country, Entry, Origin, Score, SCORE_MIN, SCORE_MAX

DATA_DIR = Path(__file__).resolve().parent
COUNTRIES_FILE = DATA_DIR / "countries.json"
DB_PATH = DATA_DIR / "compass.db"

_YEAR_RE = re.compile(r"^\d{4}$")
_countries: list[Country] | None = None
_conn: sqlite3.Connection | None = None

_SCHEMA = f"""
CREATE TABLE IF NOT EXISTS entries (
    seq              INTEGER PRIMARY KEY AUTOINCREMENT,      -- insertion order
    id               TEXT    NOT NULL UNIQUE,                -- e.g. 28092026-63.1
    country_id       INTEGER NOT NULL,
    year             TEXT    NOT NULL CHECK (length(year) = 4),
    left_right       INTEGER NOT NULL CHECK (left_right BETWEEN {SCORE_MIN} AND {SCORE_MAX}),
    lib_auth         INTEGER NOT NULL CHECK (lib_auth   BETWEEN {SCORE_MIN} AND {SCORE_MAX}),
    summary          TEXT    NOT NULL DEFAULT '',
    justification_lr TEXT    NOT NULL DEFAULT '',
    justification_la TEXT    NOT NULL DEFAULT '',
    sources          TEXT    NOT NULL DEFAULT '[]',          -- JSON list: small and never queried
    categories       TEXT    NOT NULL DEFAULT '{{}}',         -- JSON: category id -> {{score, evidence, confidence}}
    date_assessed    TEXT    NOT NULL DEFAULT '',
    origin           TEXT    NOT NULL DEFAULT 'manual' CHECK (origin IN ('manual', 'ai', 'manual_ai')),
    model            TEXT    NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_country_year ON entries (country_id, year);
"""


def _db() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(DB_PATH)
        _conn.row_factory = sqlite3.Row
        _conn.executescript(_SCHEMA)
    return _conn


def _close() -> None:
    global _conn
    if _conn is not None:
        _conn.close()
        _conn = None


def _to_entry(row: sqlite3.Row) -> Entry:
    return Entry(
        id=row["id"], left_right=row["left_right"], lib_auth=row["lib_auth"], summary=row["summary"],
        justification_lr=row["justification_lr"], justification_la=row["justification_la"],
        sources=json.loads(row["sources"]),
        categories={k: CategoryRating.from_dict(v) for k, v in json.loads(row["categories"]).items()},
        date_assessed=row["date_assessed"], origin=row["origin"], model=row["model"],
    )


# -- countries.json (unchanged: the fixed list of countries) ----------------------------------

def countries() -> list[Country]:
    global _countries
    if _countries is None:
        raw = json.loads(COUNTRIES_FILE.read_text(encoding="utf-8"))
        _countries = sorted((Country(int(c["index"]), c["name"]) for c in raw), key=lambda c: c.name)
    return _countries


def get_country(country_id: int) -> Country:
    for c in countries():
        if c.index == int(country_id):
            return c
    raise KeyError(f"Unknown country id {country_id}")


def reload() -> None:
    """Nothing is cached here (SQLite is the single source of truth); kept so callers work with both stores."""


# -- reading -----------------------------------------------------------------------------------------

def years_of(country_id: int) -> list[str]:
    rows = _db().execute("SELECT DISTINCT year FROM entries WHERE country_id = ? ORDER BY year", (int(country_id),))
    return [r["year"] for r in rows]


def entries(country_id: int, year: str) -> list[Entry]:
    rows = _db().execute("SELECT * FROM entries WHERE country_id = ? AND year = ? ORDER BY seq", (int(country_id), str(year)))
    return [_to_entry(r) for r in rows]


def all_years() -> list[str]:
    return [r["year"] for r in _db().execute("SELECT DISTINCT year FROM entries ORDER BY year DESC")]


def countries_with_data() -> list[int]:
    return [r["country_id"] for r in _db().execute("SELECT DISTINCT country_id FROM entries ORDER BY country_id")]


def entry_count(country_id: int) -> int:
    return _db().execute("SELECT COUNT(*) FROM entries WHERE country_id = ?", (int(country_id),)).fetchone()[0]


def average_scores(year: str) -> dict[int, Score]:
    """All countries' averaged score for a year in ONE query -- the JSON store has to loop for this."""
    rows = _db().execute(
        "SELECT country_id, AVG(left_right) AS lr, AVG(lib_auth) AS la, COUNT(*) AS n "
        "FROM entries WHERE year = ? GROUP BY country_id", (str(year),))
    return {r["country_id"]: Score(r["lr"], r["la"], r["n"]) for r in rows}


def category_breakdown(country_id: int, year: str) -> dict[str, float]:
    """Mean per-category score (-10..10) across entries of that year that rated it. SQL does the averaging."""
    rows = _db().execute("SELECT categories FROM entries WHERE country_id = ? AND year = ?", (int(country_id), str(year)))
    sums: dict[str, list[float]] = {}
    for row in rows:
        for cid, rating in json.loads(row["categories"]).items():
            sums.setdefault(cid, []).append(rating["score"])
    return {cid: sum(vs) / len(vs) for cid, vs in sums.items()}


# -- writing -----------------------------------------------------------------------------------------

def _validate(year: str, left_right: int, lib_auth: int) -> tuple[str, int, int]:
    year = str(year).strip()
    if not _YEAR_RE.match(year):
        raise ValueError("Year must be four digits, e.g. 2024.")
    try:
        left_right, lib_auth = int(left_right), int(lib_auth)
    except (TypeError, ValueError):
        raise ValueError("Left/Right and Lib/Auth must be whole numbers.")
    for name, v in (("Left/Right", left_right), ("Lib/Auth", lib_auth)):
        if not SCORE_MIN <= v <= SCORE_MAX:
            raise ValueError(f"{name} must be between {SCORE_MIN} and {SCORE_MAX}.")
    return year, left_right, lib_auth


def _new_id(country_id: int) -> str:
    stem = f"{date.today():%d%m%Y}-{country_id}."
    used = {r["id"] for r in _db().execute("SELECT id FROM entries WHERE country_id = ?", (country_id,))}
    n = 1
    while f"{stem}{n}" in used:
        n += 1
    return f"{stem}{n}"


def _coerce_categories(categories: dict | None) -> dict[str, CategoryRating]:
    if not categories:
        return {}
    return {k: v if isinstance(v, CategoryRating) else CategoryRating(**v) for k, v in categories.items()}


def add_entry(
    country_id: int, year: str, left_right: int | None = None, lib_auth: int | None = None, *,
    categories: dict | None = None, summary: str = "", justification_lr: str = "", justification_la: str = "",
    sources: list[str] | None = None, origin: Origin = "manual", model: str = "", date_assessed: str | None = None,
) -> Entry:
    country_id = get_country(country_id).index
    cats = _coerce_categories(categories)
    if cats and (left_right is None or lib_auth is None):
        computed_lr, computed_la = axes_from_categories({k: v.score for k, v in cats.items()})
        left_right = round(computed_lr) if left_right is None else left_right
        lib_auth = round(computed_la) if lib_auth is None else lib_auth
    if left_right is None or lib_auth is None:
        raise ValueError("Provide left_right/lib_auth, or a category breakdown to compute them from.")
    year, left_right, lib_auth = _validate(year, left_right, lib_auth)
    entry = Entry(
        id=_new_id(country_id), left_right=left_right, lib_auth=lib_auth, categories=cats, summary=summary.strip(),
        justification_lr=justification_lr.strip(), justification_la=justification_la.strip(),
        sources=[s.strip() for s in (sources or []) if s.strip()],
        date_assessed=date_assessed or date.today().isoformat(), origin=origin, model=model,
    )
    cats_json = json.dumps({k: v.to_dict() for k, v in cats.items()}, ensure_ascii=False)
    with _db() as db:                                # `with` = one transaction: commit, or roll back on error
        db.execute(
            "INSERT INTO entries (id, country_id, year, left_right, lib_auth, summary, justification_lr, "
            "justification_la, sources, categories, date_assessed, origin, model) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (entry.id, country_id, year, left_right, lib_auth, entry.summary, entry.justification_lr,
             entry.justification_la, json.dumps(entry.sources, ensure_ascii=False), cats_json,
             entry.date_assessed, origin, model))
    return entry


def update_entry(
    country_id: int, entry_id: str, *, year: str | None = None,
    left_right: int | None = None, lib_auth: int | None = None,
    categories: dict | None = None, recompute_from_categories: bool = False,
    summary: str | None = None, justification_lr: str | None = None,
    justification_la: str | None = None, sources: list[str] | None = None,
) -> Entry:
    """Editing an "ai" entry promotes its origin to "manual_ai" -- same rule as the JSON store."""
    row = _db().execute("SELECT * FROM entries WHERE id = ? AND country_id = ?", (entry_id, int(country_id))).fetchone()
    if row is None:
        raise KeyError(f"No entry {entry_id!r} for country {country_id}")
    entry = _to_entry(row)
    if categories is not None:
        entry.categories = _coerce_categories(categories)
    if recompute_from_categories and entry.categories:
        computed_lr, computed_la = axes_from_categories({k: v.score for k, v in entry.categories.items()})
        left_right = round(computed_lr) if left_right is None else left_right
        lib_auth = round(computed_la) if lib_auth is None else lib_auth
    new_year, lr, la = _validate(year if year is not None else row["year"],
                                 entry.left_right if left_right is None else left_right,
                                 entry.lib_auth if lib_auth is None else lib_auth)
    entry.left_right, entry.lib_auth = lr, la
    if summary is not None:
        entry.summary = summary.strip()
    if justification_lr is not None:
        entry.justification_lr = justification_lr.strip()
    if justification_la is not None:
        entry.justification_la = justification_la.strip()
    if sources is not None:
        entry.sources = [s.strip() for s in sources if s.strip()]
    new_origin = "manual_ai" if entry.origin == "ai" else entry.origin
    with _db() as db:
        db.execute(
            "UPDATE entries SET year=?, left_right=?, lib_auth=?, summary=?, justification_lr=?, "
            "justification_la=?, sources=?, categories=?, origin=? WHERE id=?",
            (new_year, lr, la, entry.summary, entry.justification_lr, entry.justification_la,
             json.dumps(entry.sources, ensure_ascii=False),
             json.dumps({k: v.to_dict() for k, v in entry.categories.items()}, ensure_ascii=False),
             new_origin, entry_id))
    entry.origin = new_origin
    return entry


def delete_entry(country_id: int, entry_id: str) -> None:
    with _db() as db:
        cur = db.execute("DELETE FROM entries WHERE id = ? AND country_id = ?", (entry_id, int(country_id)))
    if cur.rowcount == 0:
        raise KeyError(f"No entry {entry_id!r} for country {country_id}")


# -- one-off: copy the JSON files into the database ------------------------------------------------------------

def import_json(folder: Path | None = None) -> int:
    folder = folder or DATA_DIR / "countries"
    imported = 0
    for path in sorted(folder.glob("*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        for year, es in doc.get("years", {}).items():
            for e in es:
                exists = _db().execute("SELECT 1 FROM entries WHERE id = ?", (e["id"],)).fetchone()
                if exists:
                    continue                                   # safe to run twice
                entry = Entry.from_dict(e)
                cats_json = json.dumps({k: v.to_dict() for k, v in entry.categories.items()}, ensure_ascii=False)
                with _db() as db:
                    db.execute(
                        "INSERT INTO entries (id, country_id, year, left_right, lib_auth, summary, justification_lr, "
                        "justification_la, sources, categories, date_assessed, origin, model) "
                        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (entry.id, int(doc["country_id"]), year, entry.left_right, entry.lib_auth, entry.summary,
                         entry.justification_lr, entry.justification_la, json.dumps(entry.sources, ensure_ascii=False),
                         cats_json, entry.date_assessed, entry.origin, entry.model))
                imported += 1
    return imported


if __name__ == "__main__":
    if "--import-json" in sys.argv:
        print(f"Imported {import_json()} entries into {DB_PATH.name}.")
    else:
        print(__doc__)
