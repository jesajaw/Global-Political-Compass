"""
One-off import of the OLD format (data/country_scores.json + data/evaluations.json,
one score per country and year) into the new per-country files.

    python -m data.migrate_legacy

Only run it if those two files hold data you want to keep. Nothing is
imported automatically, and the old files are left untouched.
"""

import json

from . import store

OLD_SCORES = store.DATA_DIR / "country_scores.json"
OLD_EVALS = store.DATA_DIR / "evaluations.json"


def main() -> None:
    if not OLD_SCORES.exists():
        print("No country_scores.json found -- nothing to migrate.")
        return
    scores = json.loads(OLD_SCORES.read_text(encoding="utf-8"))
    evals = {}
    if OLD_EVALS.exists():
        evals = json.loads(OLD_EVALS.read_text(encoding="utf-8")).get("evaluations", {})

    imported = 0
    for country_id, years in scores.items():
        for year, s in years.items():
            info = evals.get(s.get("rubric_id", ""), {})
            just = info.get("justification", {})
            store.add_entry(
                int(country_id), year, s["left_right"], s["lib_auth"],
                summary=info.get("summary", ""),
                justification_lr=just.get("left_right", ""), justification_la=just.get("lib_auth", ""),
                sources=info.get("sources", []),
            )
            imported += 1
    print(f"Imported {imported} entries. You can delete the two old files now.")


if __name__ == "__main__":
    main()
