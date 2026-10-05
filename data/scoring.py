"""
Evaluation on top of the stored entries -- this is what the UI asks for.

get_score() is THE interface the compass uses: it takes a country + year and
returns the mean of all entries of that year (or None if there are none).

get_category_breakdown() additionally exposes the per-category means for the
hover tooltip -- context-only categories (Environment, Foreign Policy) included,
even though they never feed the plotted axes (see data.categories).
"""

from __future__ import annotations

from . import store
from .categories import CATEGORIES
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


def get_category_breakdown(country_id: int, year: str) -> dict[str, float]:
    """
    Mean category score (-10..10) across all entries of that year that rated it -- entries
    without a category breakdown (plain manual entries) simply don't contribute. Empty dict
    if nothing has category data. For the hover tooltip, not for the plotted axes.
    """
    entries = [e for e in store.entries(country_id, year) if e.categories]
    breakdown: dict[str, float] = {}
    for category in CATEGORIES:
        values = [e.categories[category.id].score for e in entries if category.id in e.categories]
        if values:
            breakdown[category.id] = sum(values) / len(values)
    return breakdown
