"""
Fallback data, used only if data/countries.json, data/country_scores.json
and data/evaluations.json aren't found. Same shape those real files use, so
nothing else needs to change once the real evaluation pipeline is filling
them in -- this is purely so the UI has something to render on a fresh
checkout, before scripts/agent.py has produced any real evaluations.
"""

DEFAULT_COUNTRIES = [
    {"index": 63, "name": "Germany", "code": "DE"},
    {"index": 187, "name": "United States", "code": "US"},
    {"index": 36, "name": "China", "code": "CN"},
    {"index": 170, "name": "Switzerland", "code": "CH"},
]

DEFAULT_SCORES = {
    "63": {"2024": {"left_right": -8, "lib_auth": -15, "rubric_id": "demo-de-2024"}},
    "187": {"2024": {"left_right": 12, "lib_auth": 5, "rubric_id": "demo-us-2024"}},
    "36": {"2024": {"left_right": 30, "lib_auth": 78, "rubric_id": "demo-cn-2024"}},
    "170": {"2024": {"left_right": -5, "lib_auth": -35, "rubric_id": "demo-ch-2024"}},
}

DEFAULT_EVALUATIONS = {
    "evaluations": {
        rubric_id: {
            "summary": "Placeholder -- no real evaluation yet.",
            "justification": {"left_right": "TODO", "lib_auth": "TODO"},
        }
        for rubric_id in ("demo-de-2024", "demo-us-2024", "demo-cn-2024", "demo-ch-2024")
    }
}
