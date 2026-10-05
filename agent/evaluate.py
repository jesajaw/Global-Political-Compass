"""
The AGENT: asks a local LLM (via Ollama) to rate one country for one year on all 10 categories
(see data/categories.py) in a SINGLE call, and turns the answer into a category breakdown --
data.store then derives the two compass axes from it (see store.add_entry). The agent never
writes to disk itself; the caller decides what to do with the result.

    python -m agent.evaluate Germany 2024                  # command-line run, stores the entry
    python -m agent.evaluate Germany 2024 --skip-existing   # do nothing if an agent entry already exists
    python -m agent.evaluate Germany 2024 --runs 3          # self-consistency: 3 calls, median per category

Exit codes (so scripts like batch.ps1 can react): 0 stored, 1 failed, 3 skipped.
"""

from __future__ import annotations

import json
import re
import statistics
import sys

from data.categories import CATEGORIES, CATEGORY_SCORE_MAX, CATEGORY_SCORE_MIN
from .llm_client import AgentError, MODEL, generate_json

# One call rates every category at once (10 calls -> 1), which is the main lever for keeping
# a run fast; --runs above is the (expensive, opt-in) way to add self-consistency back for a
# specific country when you want to check how stable the rating is.
PROMPT = """
Analyze the political situation in {country} for the full year {year}.

Rate the country on each of these {n} categories, independently, on a scale from -10 to +10.
For every category, -10 means "{anchors_low}" and +10 means "{anchors_high}" -- use the FULL
range where the evidence supports it, don't default to the middle.

Categories (use exactly these ids):
{category_list}

Respond EXCLUSIVELY as valid JSON: a single object whose keys are the category ids above and
whose values look like this:
{{
    "score": 0,
    "evidence": "one or two sentences of concrete, checkable evidence for this score",
    "sources": ["at least one URL where this evidence comes from"]
}}

Example shape (values illustrative only):
{{
    "economy": {{"score": 6, "evidence": "...", "sources": ["https://..."]}},
    "taxation": {{"score": -3, "evidence": "...", "sources": ["https://..."]}}
}}
"""


def _build_prompt(country: str, year: str) -> str:
    category_list = "\n".join(f'- "{c.id}": low = {c.anchor_low}; high = {c.anchor_high}' for c in CATEGORIES)
    return PROMPT.format(
        country=country, year=year, n=len(CATEGORIES), category_list=category_list,
        anchors_low="the low end described for that category below",
        anchors_high="the high end described for that category below",
    )


def _clamp_score(value) -> int:
    try:
        number = round(float(value))
    except (TypeError, ValueError):
        raise AgentError("The model returned no usable number for a category score.")
    return max(CATEGORY_SCORE_MIN, min(CATEGORY_SCORE_MAX, number))


def _extract_json(raw: str) -> dict:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)     # some models wrap the JSON in extra text
        try:
            data = json.loads(match.group(0)) if match else None
        except json.JSONDecodeError:
            data = None
    if not isinstance(data, dict):
        raise AgentError("The model did not answer with valid JSON.")
    return data


def parse(raw: str) -> dict[str, dict]:
    """Validate the model's JSON and return {category_id: {"score", "evidence", "sources"}, ...}."""
    data = _extract_json(raw)
    result = {}
    for category in CATEGORIES:
        entry = data.get(category.id)
        if not isinstance(entry, dict) or "score" not in entry:
            continue                                   # a missing category is tolerated -- axes_from_categories skips it
        sources = entry.get("sources")
        result[category.id] = {
            "score": _clamp_score(entry["score"]),
            "evidence": str(entry.get("evidence", "")),
            "sources": [str(s) for s in sources] if isinstance(sources, list) else [],
        }
    if not result:
        raise AgentError("The model's answer didn't contain any recognizable category ratings.")
    return result


def _merge_runs(runs: list[dict[str, dict]]) -> dict[str, dict]:
    """Median score per category across several runs; evidence/sources are taken from the first run that has them."""
    merged = {}
    for category in CATEGORIES:
        present = [r[category.id] for r in runs if category.id in r]
        if not present:
            continue
        merged[category.id] = {
            "score": round(statistics.median(p["score"] for p in present)),
            "evidence": next((p["evidence"] for p in present if p["evidence"]), ""),
            "sources": next((p["sources"] for p in present if p["sources"]), []),
        }
    return merged


def evaluate_country(country_name: str, year: str, runs: int = 1) -> dict[str, dict]:
    """Ask the model (runs>1: self-consistency via median). Raises AgentError with a readable message."""
    prompt = _build_prompt(country_name, year)
    results = [parse(generate_json(prompt)) for _ in range(max(1, runs))]
    return results[0] if len(results) == 1 else _merge_runs(results)


def to_store_categories(rated: dict[str, dict]) -> dict[str, dict]:
    """The category dict data.store.add_entry()/update_entry() expect. Confidence defaults to 1.0
    (a single point estimate) but is taken from `rated` if present -- that's how agent.review's
    confidence penalties (see apply_review()) make it into what's actually stored."""
    return {cid: {"score": v["score"], "evidence": v["evidence"], "confidence": v.get("confidence", 1.0)}
           for cid, v in rated.items()}


def all_sources(rated: dict[str, dict]) -> list[str]:
    seen, out = set(), []
    for v in rated.values():
        for s in v.get("sources", []):
            if s not in seen:
                seen.add(s)
                out.append(s)
    return out


def store_result(country_id: int, year: str, rated: dict[str, dict], *,
                 sources_verified: dict[str, bool] | None = None,
                 review_notes: str = "", reviewed_by: str = ""):
    """Save an evaluate_country() result as a new entry (origin="ai"). Call from the main thread."""
    from data import store

    return store.add_entry(
        country_id, year, categories=to_store_categories(rated), origin="ai", model=MODEL,
        sources=all_sources(rated), sources_verified=sources_verified or {},
        review_notes=review_notes, reviewed_by=reviewed_by,
        summary=f"Agent rating across {len(rated)}/{len(CATEGORIES)} categories.",
    )


EXIT_OK, EXIT_FAILED, EXIT_SKIPPED = 0, 1, 3


def main(argv: list[str] | None = None) -> int:
    import argparse
    from data import store

    parser = argparse.ArgumentParser(prog="python -m agent.evaluate", description="Let the agent rate one country for one year.")
    parser.add_argument("country", help='country name as in countries.json, e.g. "Germany"')
    parser.add_argument("year", help="four-digit year, e.g. 2024")
    parser.add_argument("--skip-existing", action="store_true", help="skip if an agent entry for this country and year already exists")
    parser.add_argument("--runs", type=int, default=1, help="self-consistency: call the model N times and take the median per category (default 1)")
    parser.add_argument("--verify-sources", action="store_true", help="check every cited source URL is actually reachable (agent.verify)")
    parser.add_argument("--review", action="store_true", help="have a second model red-team the ratings (agent.review) -- set AGENT_REVIEW_MODEL to a genuinely different model first")
    args = parser.parse_args(argv)

    match = next((c for c in store.countries() if c.name.lower() == args.country.lower()), None)
    if match is None:
        print(f"Unknown country: {args.country}", file=sys.stderr)
        return EXIT_FAILED
    if args.skip_existing and any(e.origin in ("ai", "manual_ai") for e in store.entries(match.index, args.year)):
        print(f"Skipped: {match.name} {args.year} already has an agent entry.")
        return EXIT_SKIPPED
    try:
        rated = evaluate_country(match.name, args.year, runs=args.runs)

        sources_verified = None
        if args.verify_sources:
            from .verify import verify_sources
            sources_verified = verify_sources(all_sources(rated))
            dead = [u for u, ok in sources_verified.items() if not ok]
            if dead:
                print(f"Warning: {len(dead)} source(s) unreachable: {', '.join(dead)}", file=sys.stderr)

        review_notes, reviewed_by = "", ""
        if args.review:
            from .review import review, apply_review, REVIEW_MODEL
            result = review(match.name, args.year, rated)
            rated, review_notes = apply_review(rated, result)
            reviewed_by = REVIEW_MODEL
            if result["concerns"]:
                print(f"Review flagged {len(result['concerns'])} categor{'y' if len(result['concerns']) == 1 else 'ies'}.")

        entry = store_result(match.index, args.year, rated,
                            sources_verified=sources_verified, review_notes=review_notes, reviewed_by=reviewed_by)
    except (AgentError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return EXIT_FAILED
    print(f"Stored {entry.id}: L/R {entry.left_right}, Lib/Auth {entry.lib_auth} "
         f"({len(rated)}/{len(CATEGORIES)} categories rated).")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
