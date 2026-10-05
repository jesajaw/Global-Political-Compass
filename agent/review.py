"""
Red-team pass: a second model looks at the FIRST model's category ratings + evidence for one
country/year and is asked to find what's weakly supported, one-sided, or contradicted -- not to
just rubber-stamp it. Two models sharing the same training data and the same lean will tend to
share the same blind spots, so this is only really doing its job if AGENT_REVIEW_MODEL is a
genuinely different model (different lab if possible), not the same one twice.

Configure via:
    AGENT_REVIEW_BACKEND   "ollama" or "api" (default: same as AGENT_BACKEND)
    AGENT_REVIEW_MODEL     defaults to MODEL if unset -- i.e. reviewing with itself, which is
                           allowed (still catches some internal inconsistency/missing evidence)
                           but is the weaker option; set this explicitly to a different model.
    AGENT_REVIEW_API_BASE_URL / AGENT_REVIEW_API_KEY   only needed if the review backend is "api"
                           and its provider differs from the main one.

The review does not silently rewrite scores. It can only LOWER a category's confidence (never
raise it, never touch the score itself) and leaves a human-readable note -- adjusting the actual
rating is left to a person, via the Data window.
"""

from __future__ import annotations

import json
import os
import re

from data.categories import CATEGORY_BY_ID
from . import llm_client
from .llm_client import AgentError

REVIEW_BACKEND = os.environ.get("AGENT_REVIEW_BACKEND", llm_client.BACKEND)
REVIEW_MODEL = os.environ.get("AGENT_REVIEW_MODEL", llm_client.MODEL)
REVIEW_API_BASE_URL = os.environ.get("AGENT_REVIEW_API_BASE_URL", llm_client.API_BASE_URL)
REVIEW_API_KEY = os.environ.get("AGENT_REVIEW_API_KEY", llm_client.API_KEY)

PROMPT = """
You are red-teaming another AI's political rating of {country} for {year}. For each category
below, you're given the score it gave (-10..+10) and its evidence. Be skeptical: look for
categories that are asserted without real evidence, evidence that doesn't actually support the
direction of the score, or an obviously one-sided framing.

Ratings to review:
{ratings}

Respond EXCLUSIVELY as valid JSON:
{{
    "concerns": [
        {{"category": "<category id from the list above>", "comment": "short, specific problem you see",
         "confidence_penalty": 0.3}}
    ],
    "notes": "one or two sentences summarizing your overall take"
}}
"concerns" can be empty if you find nothing worth flagging. "confidence_penalty" is how much to
lower that category's confidence by, between 0 (trivial concern) and 1 (no real evidence at all).
"""


def _generate(prompt: str) -> str:
    """Same protocol as llm_client.generate_json, but against the review backend/model."""
    if REVIEW_BACKEND == "ollama":
        original = llm_client.MODEL
        llm_client.MODEL = REVIEW_MODEL          # evaluate.py never touches this module directly, so a brief swap is safe
        try:
            return llm_client._generate_ollama(prompt)
        finally:
            llm_client.MODEL = original
    if REVIEW_BACKEND == "api":
        original = (llm_client.MODEL, llm_client.API_BASE_URL, llm_client.API_KEY)
        llm_client.MODEL, llm_client.API_BASE_URL, llm_client.API_KEY = REVIEW_MODEL, REVIEW_API_BASE_URL, REVIEW_API_KEY
        try:
            return llm_client._generate_api(prompt)
        finally:
            llm_client.MODEL, llm_client.API_BASE_URL, llm_client.API_KEY = original
    raise AgentError(f'Unknown AGENT_REVIEW_BACKEND "{REVIEW_BACKEND}".')


def _format_ratings(rated: dict[str, dict]) -> str:
    lines = []
    for cid, r in rated.items():
        category = CATEGORY_BY_ID.get(cid)
        label = category.label if category else cid
        lines.append(f'- "{cid}" ({label}): score={r["score"]}, evidence="{r.get("evidence", "")}"')
    return "\n".join(lines)


def _parse(raw: str) -> dict:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        try:
            data = json.loads(match.group(0)) if match else None
        except json.JSONDecodeError:
            data = None
    if not isinstance(data, dict):
        raise AgentError("The review model did not answer with valid JSON.")
    concerns = data.get("concerns")
    if not isinstance(concerns, list):
        concerns = []
    cleaned = []
    for c in concerns:
        if not isinstance(c, dict) or c.get("category") not in CATEGORY_BY_ID:
            continue                                    # ignore a concern about a category that doesn't exist
        try:
            penalty = max(0.0, min(1.0, float(c.get("confidence_penalty", 0))))
        except (TypeError, ValueError):
            penalty = 0.0
        cleaned.append({"category": c["category"], "comment": str(c.get("comment", "")), "confidence_penalty": penalty})
    return {"concerns": cleaned, "notes": str(data.get("notes", ""))}


def review(country_name: str, year: str, rated: dict[str, dict]) -> dict:
    """Ask the review model to critique `rated` (evaluate.evaluate_country()'s output)."""
    prompt = PROMPT.format(country=country_name, year=year, ratings=_format_ratings(rated))
    return _parse(_generate(prompt))


def apply_review(rated: dict[str, dict], review_result: dict) -> tuple[dict[str, dict], str]:
    """
    Applies confidence penalties from review() onto a copy of `rated` (never touches scores),
    and builds the note text to store. Returns (adjusted_rated, review_notes_text).
    """
    adjusted = {cid: dict(r) for cid, r in rated.items()}
    lines = []
    for concern in review_result["concerns"]:
        cid = concern["category"]
        if cid in adjusted:
            current = adjusted[cid].get("confidence", 1.0)
            adjusted[cid]["confidence"] = max(0.0, current - concern["confidence_penalty"])
        label = CATEGORY_BY_ID[cid].label if cid in CATEGORY_BY_ID else cid
        lines.append(f"- {label}: {concern['comment']}")
    if review_result.get("notes"):
        lines.append(review_result["notes"])
    return adjusted, "\n".join(lines)
