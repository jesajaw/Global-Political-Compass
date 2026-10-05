"""
Plain data containers shared by all three areas (ui / agent / data).

Nothing here touches files or widgets -- store.py (persistence) and
scoring.py (evaluation) build on these, ui/ and agent/ only ever see these.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Literal

SCORE_MIN = -100
SCORE_MAX = 100

# manual: entered by hand, no agent involved
# ai: written by the agent, never reviewed by a person
# manual_ai: started as an agent entry, a person then edited/reviewed it
Origin = Literal["manual", "ai", "manual_ai"]
ORIGINS: tuple[Origin, ...] = ("manual", "ai", "manual_ai")


@dataclass(frozen=True)
class Country:
    index: int
    name: str


@dataclass(frozen=True)
class CategoryRating:
    """One category's rating within an entry -- see data/categories.py for what the id means."""
    score: int                 # -10..+10, see data.categories.CATEGORY_SCORE_MIN/MAX
    evidence: str = ""
    confidence: float = 1.0    # 0..1; manual ratings default to 1.0 (a person vouches for it)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "CategoryRating":
        return cls(score=int(d["score"]), evidence=d.get("evidence", ""), confidence=float(d.get("confidence", 1.0)))


@dataclass
class Entry:
    """
    One single assessment of one country for one year. A year can hold many.

    left_right/lib_auth are always the two numbers the compass plots (-100..100), no matter
    where they came from. If `categories` is filled in, they were computed FROM the categories
    (see data.categories.axes_from_categories) at save time and shouldn't be hand-edited without
    also updating the categories -- store.update_entry() enforces that. A quick manual entry
    with no category breakdown is just as valid; `categories` stays empty for it.
    """
    id: str
    left_right: int
    lib_auth: int
    categories: dict[str, CategoryRating] = field(default_factory=dict)   # category id -> rating
    summary: str = ""
    justification_lr: str = ""
    justification_la: str = ""
    sources: list[str] = field(default_factory=list)
    sources_verified: dict[str, bool] = field(default_factory=dict)   # source URL -> reachable? (agent.verify); absent = never checked
    date_assessed: str = ""
    origin: Origin = "manual"
    model: str = ""              # which model produced this (ai/manual_ai only); "" for manual
    review_notes: str = ""       # a second model's critique of this entry's ratings, if reviewed (agent.review)
    reviewed_by: str = ""        # which model wrote review_notes; "" if never reviewed

    def to_dict(self) -> dict:
        d = asdict(self)
        d["justification"] = {"left_right": d.pop("justification_lr"), "lib_auth": d.pop("justification_la")}
        d["categories"] = {k: v.to_dict() for k, v in self.categories.items()}
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Entry":
        just = d.get("justification", {})
        origin = d.get("origin", "manual")
        if origin not in ORIGINS:                 # tolerate data written before manual_ai existed
            origin = "manual"
        return cls(
            id=d["id"],
            left_right=int(d["left_right"]),
            lib_auth=int(d["lib_auth"]),
            categories={k: CategoryRating.from_dict(v) for k, v in d.get("categories", {}).items()},
            summary=d.get("summary", ""),
            justification_lr=just.get("left_right", ""),
            justification_la=just.get("lib_auth", ""),
            sources=list(d.get("sources", [])),
            sources_verified=dict(d.get("sources_verified", {})),
            date_assessed=d.get("date_assessed", ""),
            origin=origin,
            model=d.get("model", ""),
            review_notes=d.get("review_notes", ""),
            reviewed_by=d.get("reviewed_by", ""),
        )


@dataclass(frozen=True)
class Score:
    """The evaluated result for one country + year: the mean of all its entries."""
    left_right: float
    lib_auth: float
    count: int
