"""
CSV export for external analysis (spreadsheet, R, pandas, ...) -- the JSON/SQLite stores are
the source of truth, this is a read-only, one-way snapshot.

    python -m data.export                       # every entry, every country/year -> stdout
    python -m data.export --year 2024            # just one year
    python -m data.export --out entries.csv      # write to a file instead of stdout
    python -m data.export --scores --year 2024   # one row per country: the averaged score
                                                   # the compass actually plots, not raw entries
"""

from __future__ import annotations

import csv
import sys

from . import scoring, store
from .categories import CATEGORIES

ENTRY_FIELDS = [
    "country", "country_id", "year", "entry_id", "left_right", "lib_auth", "origin", "model",
    "reviewed_by", "summary", "sources", "sources_verified",
] + [f"cat_{c.id}" for c in CATEGORIES]

SCORE_FIELDS = ["country", "country_id", "year", "left_right", "lib_auth", "entry_count"]


def _entry_row(country_name: str, country_id: int, year: str, entry) -> dict:
    row = {
        "country": country_name, "country_id": country_id, "year": year, "entry_id": entry.id,
        "left_right": entry.left_right, "lib_auth": entry.lib_auth, "origin": entry.origin,
        "model": entry.model, "reviewed_by": entry.reviewed_by, "summary": entry.summary,
        "sources": "; ".join(entry.sources),
        "sources_verified": "; ".join(f"{u}={'ok' if ok else 'dead'}" for u, ok in entry.sources_verified.items()),
    }
    for c in CATEGORIES:
        rating = entry.categories.get(c.id)
        row[f"cat_{c.id}"] = rating.score if rating else ""
    return row


def entry_rows(year: str | None = None) -> list[dict]:
    countries = {c.index: c.name for c in store.countries()}
    rows = []
    for country_id in store.countries_with_data():
        years = [year] if year else store.years_of(country_id)
        for y in years:
            for entry in store.entries(country_id, y):
                rows.append(_entry_row(countries[country_id], country_id, y, entry))
    return rows


def score_rows(year: str | None = None) -> list[dict]:
    countries = {c.index: c.name for c in store.countries()}
    years = [year] if year else store.all_years()
    rows = []
    for y in years:
        for country_id, score in scoring.get_scores(y).items():
            rows.append({"country": countries[country_id], "country_id": country_id, "year": y,
                        "left_right": round(score.left_right, 1), "lib_auth": round(score.lib_auth, 1),
                        "entry_count": score.count})
    return rows


def write_csv(rows: list[dict], fields: list[str], out) -> None:
    writer = csv.DictWriter(out, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="python -m data.export", description="Export stored entries or averaged scores as CSV.")
    parser.add_argument("--year", help="only this year (default: every year)")
    parser.add_argument("--scores", action="store_true", help="export the averaged per-country score instead of raw entries")
    parser.add_argument("--out", help="write to this file instead of stdout")
    args = parser.parse_args(argv)

    if args.scores:
        rows, fields = score_rows(args.year), SCORE_FIELDS
    else:
        rows, fields = entry_rows(args.year), ENTRY_FIELDS

    if args.out:
        with open(args.out, "w", newline="", encoding="utf-8") as f:
            write_csv(rows, fields, f)
        print(f"Wrote {len(rows)} row(s) to {args.out}.", file=sys.stderr)
    else:
        write_csv(rows, fields, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
