"""
Measures the agent's systematic bias against a small set of reference countries whose position
you trust from an INDEPENDENT source (not the agent), and suggests a correction.

    python -m data.calibrate --reference data/reference_countries.example.json --year 2024

For each reference country, this rates it with the agent (fresh call, ignores any existing
entries) and compares to the reference value. The systematic offset (agent minus reference,
averaged) is what data.categories.CORRECTION_LR/LA exist to cancel out -- this script only
SUGGESTS a value and prints how to set it; it never edits categories.py itself, since applying a
correction silently would be exactly the "objective-looking but isn't" problem this is meant to
avoid. Read the numbers, decide if they're trustworthy, then edit categories.py yourself.

Caveats this can't fix: a handful of reference countries is a small, possibly unrepresentative
sample; your reference values are only as good as their source; and a single offset applied to
every country assumes the bias is uniform, which it may well not be (e.g. the agent could be
more skewed on some regions/categories than others -- this script can't detect that, it only
gives you the average).
"""

from __future__ import annotations

import json
import statistics
import sys

from . import store
from .categories import CATEGORY_SCORE_MAX


def load_reference(path: str) -> list[dict]:
    data = json.loads(open(path, encoding="utf-8").read())
    return data["countries"]


def measure(reference: list[dict], runs: int = 1) -> dict:
    from agent.evaluate import evaluate_country
    from agent.llm_client import AgentError
    from .categories import axes_from_categories

    diffs_lr, diffs_la, rows = [], [], []
    for ref in reference:
        match = next((c for c in store.countries() if c.name.lower() == ref["name"].lower()), None)
        if match is None:
            print(f"Skipping '{ref['name']}': not in countries.json.", file=sys.stderr)
            continue
        try:
            rated = evaluate_country(match.name, ref["year"], runs=runs)
        except AgentError as e:
            print(f"Skipping '{ref['name']}': {e}", file=sys.stderr)
            continue
        agent_lr, agent_la = axes_from_categories({cid: v["score"] for cid, v in rated.items()})
        diff_lr, diff_la = agent_lr - ref["left_right"], agent_la - ref["lib_auth"]
        diffs_lr.append(diff_lr)
        diffs_la.append(diff_la)
        rows.append({"country": match.name, "year": ref["year"],
                    "agent_lr": round(agent_lr, 1), "ref_lr": ref["left_right"], "diff_lr": round(diff_lr, 1),
                    "agent_la": round(agent_la, 1), "ref_la": ref["lib_auth"], "diff_la": round(diff_la, 1)})

    return {
        "rows": rows,
        "suggested_correction_lr": round(statistics.mean(diffs_lr), 1) if diffs_lr else 0.0,
        "suggested_correction_la": round(statistics.mean(diffs_la), 1) if diffs_la else 0.0,
        "spread_lr": round(statistics.pstdev(diffs_lr), 1) if len(diffs_lr) > 1 else 0.0,
        "spread_la": round(statistics.pstdev(diffs_la), 1) if len(diffs_la) > 1 else 0.0,
    }


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="python -m data.calibrate", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--reference", required=True, help="path to a reference countries JSON (see data/reference_countries.example.json)")
    parser.add_argument("--runs", type=int, default=1, help="self-consistency runs per country (default 1)")
    args = parser.parse_args(argv)

    reference = load_reference(args.reference)
    if any(c.get("source", "").startswith("REPLACE ME") for c in reference):
        print("Warning: this reference file still has placeholder 'REPLACE ME' sources -- "
             "the result below is not trustworthy until you cite real ones.\n", file=sys.stderr)

    result = measure(reference, runs=args.runs)
    for row in result["rows"]:
        print(f"{row['country']} {row['year']}: agent L/R={row['agent_lr']} vs ref={row['ref_lr']} "
             f"(diff {row['diff_lr']:+}) | agent Lib/Auth={row['agent_la']} vs ref={row['ref_la']} (diff {row['diff_la']:+})")

    print(f"\nSuggested CORRECTION_LR = {result['suggested_correction_lr']}   (spread across countries: {result['spread_lr']})")
    print(f"Suggested CORRECTION_LA = {result['suggested_correction_la']}   (spread across countries: {result['spread_la']})")
    print(f"\nA large spread relative to the {CATEGORY_SCORE_MAX*10}-point axis range means the bias isn't "
         "uniform across countries -- a single correction number is a weaker fix in that case.")
    print("\nIf you trust this, set these two constants by hand in data/categories.py "
         "(CORRECTION_LR / CORRECTION_LA) -- this script does not edit that file for you.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
