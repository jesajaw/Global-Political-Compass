"""
Evaluation on top of the stored entries -- this is what the UI asks for.

get_score() is THE interface the compass uses: it takes a country + year and
returns the mean of all entries of that year (or None if there are none).
"""

from __future__ import annotations

from . import store
from .models import Score


def _mean(entries) -> Score:
    n = len(entries)
    return Score(
        left_right=sum(e.left_right for e in entries) / n,
        lib_auth=sum(e.lib_auth for e in entries) / n,
        count=n,
    )


def get_score(country_id: int, year: str) -> Score | None:
    entries = store.entries(country_id, year)
    return _mean(entries) if entries else None


def get_scores(year: str) -> dict[int, Score]:
    """All countries that have data for `year` -> their averaged score (what the compass plots)."""
    result = {}
    for country_id in store.countries_with_data():
        score = get_score(country_id, year)
        if score:
            result[country_id] = score
    return result


def yearly_scores(country_id: int) -> dict[str, Score]:
    """One country's averaged score for every year it has data for, oldest first."""
    return {y: _mean(store.entries(country_id, y)) for y in store.years_of(country_id)}
