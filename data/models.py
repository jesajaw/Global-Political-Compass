"""
Plain data containers shared by all three areas (ui / agent / data).

Nothing here touches files or widgets -- store.py (persistence) and
scoring.py (evaluation) build on these, ui/ and agent/ only ever see these.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict

SCORE_MIN = -100
SCORE_MAX = 100


@dataclass(frozen=True)
class Country:
    index: int
    name: str


@dataclass
class Entry:
    """One single assessment of one country for one year. A year can hold many."""
    id: str
    left_right: int
    lib_auth: int
    summary: str = ""
    justification_lr: str = ""
    justification_la: str = ""
    sources: list[str] = field(default_factory=list)
    date_assessed: str = ""
    origin: str = "manual"          # "manual" or "agent"

    def to_dict(self) -> dict:
        d = asdict(self)
        d["justification"] = {"left_right": d.pop("justification_lr"), "lib_auth": d.pop("justification_la")}
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Entry":
        just = d.get("justification", {})
        return cls(
            id=d["id"],
            left_right=int(d["left_right"]),
            lib_auth=int(d["lib_auth"]),
            summary=d.get("summary", ""),
            justification_lr=just.get("left_right", ""),
            justification_la=just.get("lib_auth", ""),
            sources=list(d.get("sources", [])),
            date_assessed=d.get("date_assessed", ""),
            origin=d.get("origin", "manual"),
        )


@dataclass(frozen=True)
class Score:
    """The evaluated result for one country + year: the mean of all its entries."""
    left_right: float
    lib_auth: float
    count: int
