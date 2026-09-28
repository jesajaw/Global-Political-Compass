"""
Persistence: countries.json (the fixed list of countries, never written) and
one JSON file per country in data/countries/<index>.json.

A country's file does NOT exist until the first entry is added for it, and it
is removed again when its last entry is deleted -- so the folder only ever
contains countries that actually have data. There is no demo/default data.

File format (human-readable, one file per country):

    {
      "country_id": 63,
      "name": "Germany",
      "years": {
        "2024": [
          {"id": "28092026-63.1", "left_right": -25, "lib_auth": -40,
           "summary": "...", "justification": {"left_right": "...", "lib_auth": "..."},
           "sources": ["https://..."], "date_assessed": "2026-09-28", "origin": "manual"},
          ...more entries for the same year...
        ]
      }
    }

Everything is read into memory once (at most ~195 small files) and every
change is written straight back to disk, atomically.
"""

from __future__ import annotations

import json
import os
import re
from datetime import date
from pathlib import Path

from .models import Country, Entry, SCORE_MIN, SCORE_MAX

DATA_DIR = Path(__file__).resolve().parent
COUNTRIES_FILE = DATA_DIR / "countries.json"
COUNTRY_DIR = DATA_DIR / "countries"

_YEAR_RE = re.compile(r"^\d{4}$")

_countries: list[Country] | None = None
_docs: dict[int, dict[str, list[Entry]]] | None = None   # country_id -> year -> entries


# -- countries.json -----------------------------------------------------------

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


# -- loading / saving -----------------------------------------------------------

def _path(country_id: int) -> Path:
    return COUNTRY_DIR / f"{int(country_id)}.json"


def _load_all() -> dict[int, dict[str, list[Entry]]]:
    global _docs
    if _docs is None:
        _docs = {}
        if COUNTRY_DIR.exists():
            for path in sorted(COUNTRY_DIR.glob("*.json")):
                try:
                    doc = json.loads(path.read_text(encoding="utf-8"))
                    years = {y: [Entry.from_dict(e) for e in entries] for y, entries in doc.get("years", {}).items()}
                    years = {y: es for y, es in years.items() if es}
                    if years:
                        _docs[int(doc["country_id"])] = years
                except Exception as e:  # one broken file must not take the whole app down
                    print(f"Could not read {path.name} ({e}), skipping it.")
    return _docs


def reload() -> None:
    """Forget the in-memory copy and re-read everything from disk (e.g. after editing files by hand)."""
    global _docs
    _docs = None
    _load_all()


def _write(country_id: int) -> None:
    years = _load_all().get(country_id)
    path = _path(country_id)
    if not years:
        path.unlink(missing_ok=True)          # last entry gone -> file gone
        return
    COUNTRY_DIR.mkdir(parents=True, exist_ok=True)
    doc = {
        "country_id": country_id,
        "name": get_country(country_id).name,
        "years": {y: [e.to_dict() for e in years[y]] for y in sorted(years)},
    }
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)                      # atomic: never leaves a half-written file


# -- reading ----------------------------------------------------------------------

def years_of(country_id: int) -> list[str]:
    return sorted(_load_all().get(int(country_id), {}))


def entries(country_id: int, year: str) -> list[Entry]:
    return list(_load_all().get(int(country_id), {}).get(str(year), []))


def all_years() -> list[str]:
    """Every year that has at least one entry for any country, newest first."""
    return sorted({y for years in _load_all().values() for y in years}, reverse=True)


def countries_with_data() -> list[int]:
    return sorted(_load_all())


def entry_count(country_id: int) -> int:
    return sum(len(es) for es in _load_all().get(int(country_id), {}).values())


# -- writing ----------------------------------------------------------------------

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
    # same scheme as the old rubric ids: <ddmmyyyy>-<country>.<n>, n counts up per country and day
    stem = f"{date.today():%d%m%Y}-{country_id}."
    used = {e.id for es in _load_all().get(country_id, {}).values() for e in es}
    n = 1
    while f"{stem}{n}" in used:
        n += 1
    return f"{stem}{n}"


def add_entry(
    country_id: int, year: str, left_right: int, lib_auth: int, *,
    summary: str = "", justification_lr: str = "", justification_la: str = "",
    sources: list[str] | None = None, origin: str = "manual",
) -> Entry:
    country_id = get_country(country_id).index          # raises for unknown ids
    year, left_right, lib_auth = _validate(year, left_right, lib_auth)
    entry = Entry(
        id=_new_id(country_id), left_right=left_right, lib_auth=lib_auth,
        summary=summary.strip(), justification_lr=justification_lr.strip(),
        justification_la=justification_la.strip(), sources=[s.strip() for s in (sources or []) if s.strip()],
        date_assessed=date.today().isoformat(), origin=origin,
    )
    _load_all().setdefault(country_id, {}).setdefault(year, []).append(entry)
    _write(country_id)                                  # this is where the country's file gets created
    return entry


def update_entry(
    country_id: int, entry_id: str, *, year: str | None = None,
    left_right: int | None = None, lib_auth: int | None = None,
    summary: str | None = None, justification_lr: str | None = None,
    justification_la: str | None = None, sources: list[str] | None = None,
) -> Entry:
    """Adjust an existing entry. Passing a different `year` moves it to that year."""
    country_id = int(country_id)
    old_year, entry = _find(country_id, entry_id)
    new_year, lr, la = _validate(
        year if year is not None else old_year,
        entry.left_right if left_right is None else left_right,
        entry.lib_auth if lib_auth is None else lib_auth,
    )
    entry.left_right, entry.lib_auth = lr, la
    if summary is not None:
        entry.summary = summary.strip()
    if justification_lr is not None:
        entry.justification_lr = justification_lr.strip()
    if justification_la is not None:
        entry.justification_la = justification_la.strip()
    if sources is not None:
        entry.sources = [s.strip() for s in sources if s.strip()]
    if new_year != old_year:
        years = _load_all()[country_id]
        years[old_year].remove(entry)
        if not years[old_year]:
            del years[old_year]
        years.setdefault(new_year, []).append(entry)
    _write(country_id)
    return entry


def delete_entry(country_id: int, entry_id: str) -> None:
    country_id = int(country_id)
    year, entry = _find(country_id, entry_id)
    years = _load_all()[country_id]
    years[year].remove(entry)
    if not years[year]:
        del years[year]
    if not years:
        del _load_all()[country_id]
    _write(country_id)


def _find(country_id: int, entry_id: str) -> tuple[str, Entry]:
    for year, es in _load_all().get(country_id, {}).items():
        for e in es:
            if e.id == entry_id:
                return year, e
    raise KeyError(f"No entry {entry_id!r} for country {country_id}")
