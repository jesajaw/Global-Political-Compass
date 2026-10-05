"""
The 10 categories the agent rates a country/year on, and how they roll up into the two
compass axes. This is the ONLY place that decides "which category feeds which axis" --
scoring.py and the agent both import from here, so the mapping is defined exactly once.

Each category's weight is +1 (pushes the axis toward its positive/right or
positive/authoritarian end), -1 (pushes the other way) or 0 (context only, not plotted).
A category with weight 0 on both axes still gets rated and shown on hover -- it's just
not averaged into either number on the compass.
"""

from __future__ import annotations

from dataclasses import dataclass

CATEGORY_SCORE_MIN = -10
CATEGORY_SCORE_MAX = 10


@dataclass(frozen=True)
class Category:
    id: str                 # stable key, used in storage -- never rename, add a new id instead
    label: str               # shown in the UI
    axis_lr: int              # -1, 0 or +1: contribution to Left(-)/Right(+)
    axis_la: int              # -1, 0 or +1: contribution to Libertarian(-)/Authoritarian(+)
    anchor_low: str            # what -10 means, concretely (not "very left")
    anchor_high: str          # what +10 means, concretely


CATEGORIES: list[Category] = [
    Category("economy", "Economy", axis_lr=1, axis_la=0,
             anchor_low="Planned/command economy, heavy market regulation",
             anchor_high="Free-market economy, minimal regulation"),
    Category("taxation", "Taxation", axis_lr=1, axis_la=0,
             anchor_low="High, steeply progressive taxation and redistribution",
             anchor_high="Low, flat taxation"),
    Category("social_policy", "Social Policy", axis_lr=1, axis_la=0,
             anchor_low="Extensive universal welfare state",
             anchor_high="Minimal welfare, individual responsibility"),
    Category("state_ownership", "State Ownership", axis_lr=1, axis_la=0,
             anchor_low="Key industries state-owned/nationalized",
             anchor_high="Industries fully privatized"),
    Category("migration", "Migration", axis_lr=0, axis_la=1,
             anchor_low="Open borders, minimal restrictions",
             anchor_high="Tightly controlled/closed borders"),
    Category("civil_liberties", "Civil Liberties", axis_lr=0, axis_la=-1,
             anchor_low="State surveillance/control of speech, press, assembly",
             anchor_high="Strong protection of speech, press, assembly, privacy"),
    Category("law_and_order", "Law & Order", axis_lr=0, axis_la=1,
             anchor_low="Minimal policing, rehabilitation-focused justice",
             anchor_high="Heavy policing, strict/punitive justice system"),
    Category("nationalism", "Nationalism / Internationalism", axis_lr=0, axis_la=1,
             anchor_low="Internationalist, pools sovereignty (e.g. EU-style integration)",
             anchor_high="Nationalist, prioritizes sovereignty over international bodies"),
    Category("environment", "Environment", axis_lr=0, axis_la=0,
             anchor_low="Environment subordinated to growth/industry",
             anchor_high="Environmental protection prioritized, strict regulation"),
    Category("foreign_policy", "Foreign Policy", axis_lr=0, axis_la=0,
             anchor_low="Interventionist/expansionist posture",
             anchor_high="Non-interventionist/isolationist posture"),
]

CATEGORY_BY_ID = {c.id: c for c in CATEGORIES}
LR_CATEGORIES = [c for c in CATEGORIES if c.axis_lr]
LA_CATEGORIES = [c for c in CATEGORIES if c.axis_la]
CONTEXT_ONLY_CATEGORIES = [c for c in CATEGORIES if not c.axis_lr and not c.axis_la]


# Empirical calibration hook: leave at 0.0 until you've actually measured a bias. To calibrate,
# rate a handful of reference countries whose position you know from an independent source (e.g.
# an economic-freedom index for left_right, Freedom House for lib_auth), compare to what the
# agent produced, and set the systematic offset you find here (in the same -100..100 units the
# compass uses). This is intentionally NOT auto-derived from third-party model benchmarks like
# neutralityproject.org -- those measure different political dimensions than these 10 categories,
# so borrowing their number would be a guess dressed up as a measurement.
CORRECTION_LR = 0.0
CORRECTION_LA = 0.0


def axes_from_categories(category_scores: dict) -> tuple[float, float]:
    """
    category_scores: {category_id: value in [-10, 10]}. Returns (left_right, lib_auth) on the
    usual -100..100 scale: the signed mean of each axis's categories, *10. A category the
    caller didn't provide is simply left out of that axis's mean (not treated as 0), so a
    partial rating still produces a reasonable position instead of being dragged to the centre.
    """
    def mean_axis(cats: list[Category], weight_attr: str) -> float:
        values = [category_scores[c.id] * getattr(c, weight_attr) for c in cats if c.id in category_scores]
        return (sum(values) / len(values)) * 10 if values else 0.0

    lr = mean_axis(LR_CATEGORIES, "axis_lr")
    la = mean_axis(LA_CATEGORIES, "axis_la")
    return (lr - CORRECTION_LR if lr else lr), (la - CORRECTION_LA if la else la)
