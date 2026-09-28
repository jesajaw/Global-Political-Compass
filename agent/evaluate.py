"""
The AGENT: asks a local LLM (via Ollama) to rate one country for one year on
the two compass axes and turns the answer into the same fields a manual
entry has. It never writes to disk itself -- the caller decides what to do
with the result (the Data window stores it with origin="agent").

    python -m agent.evaluate Germany 2024     # quick command-line run, stores the entry
"""

from __future__ import annotations

import json
import re
import sys

from data.models import SCORE_MIN, SCORE_MAX
from .ollama import AgentError, generate_json

PROMPT = """
Analyze the political situation in {country} for the full year {year}.

Rate the country on two axes ranging from -100 to +100:
- left_right: -100 (Left/Planned economy) to +100 (Right/Free market)
- lib_auth: -100 (liberal/libertarian) to +100 (authoritarian/state control)

Respond EXCLUSIVELY as valid JSON in the following format:
{{
    "left_right": 0,
    "lib_auth": 0,
    "summary": "just a title or up to 4-5 words",
    "justification": {{
        "left_right": "a simple and short justification",
        "lib_auth": "a simple and short justification"
    }},
    "sources": ["at least one link / source where you got this information"]
}}
"""


def _score(value, name: str) -> int:
    try:
        number = round(float(value))
    except (TypeError, ValueError):
        raise AgentError(f"The model returned no usable number for {name}.")
    return max(SCORE_MIN, min(SCORE_MAX, number))       # models sometimes overshoot; clamp instead of failing


def parse(raw: str) -> dict:
    """Validate the model's JSON and return it as keyword arguments for store.add_entry()."""
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

    just = data.get("justification") if isinstance(data.get("justification"), dict) else {}
    sources = data.get("sources")
    return {
        "left_right": _score(data.get("left_right"), "left_right"),
        "lib_auth": _score(data.get("lib_auth"), "lib_auth"),
        "summary": str(data.get("summary", "")),
        "justification_lr": str(just.get("left_right", "")),
        "justification_la": str(just.get("lib_auth", "")),
        "sources": [str(s) for s in sources] if isinstance(sources, list) else [],
    }


def evaluate_country(country_name: str, year: str) -> dict:
    """Ask the model. Raises AgentError with a readable message on any failure."""
    return parse(generate_json(PROMPT.format(country=country_name, year=year)))


def store_result(country_id: int, year: str, result: dict):
    """Save an evaluate_country() result as a new entry (origin="agent"). Call from the main thread."""
    from data import store

    fields = dict(result)
    return store.add_entry(country_id, year, fields.pop("left_right"), fields.pop("lib_auth"),
                           origin="agent", **fields)


if __name__ == "__main__":
    from data import store

    if len(sys.argv) != 3:
        sys.exit("usage: python -m agent.evaluate <country name> <year>")
    name, year = sys.argv[1], sys.argv[2]
    match = next((c for c in store.countries() if c.name.lower() == name.lower()), None)
    if match is None:
        sys.exit(f"Unknown country: {name}")
    try:
        entry = store_result(match.index, year, evaluate_country(match.name, year))
    except (AgentError, ValueError) as e:
        sys.exit(str(e))
    print(f"Stored {entry.id}: L/R {entry.left_right}, Lib/Auth {entry.lib_auth} -- {entry.summary}")
