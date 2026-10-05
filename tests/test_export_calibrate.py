"""data/export.py (CSV) and data/calibrate.py (bias measurement against reference countries)."""

import csv
import io
import json
import tempfile
from pathlib import Path

from ._helpers import fresh_store


def _test_export() -> None:
    store = fresh_store()
    from data.categories import CATEGORIES
    import data.export as ex

    store.add_entry(63, "2024", 10, -20, summary="manual one")
    cats = {c.id: {"score": 3, "evidence": "e"} for c in CATEGORIES}
    store.add_entry(63, "2024", categories=cats, origin="ai", model="llama3.3:70b",
                    sources=["https://a"], sources_verified={"https://a": True})
    store.add_entry(64, "2023", 5, 5)

    rows = ex.entry_rows()
    assert len(rows) == 3
    ai_row = next(r for r in rows if r["country"] == "Germany" and r["origin"] == "ai")
    assert ai_row["cat_economy"] == 3 and ai_row["sources_verified"] == "https://a=ok"

    assert len(ex.entry_rows("2024")) == 2 and len(ex.entry_rows("2023")) == 1

    scores = ex.score_rows("2024")
    assert len(scores) == 1 and scores[0]["entry_count"] == 2

    buf = io.StringIO()
    ex.write_csv(rows, ex.ENTRY_FIELDS, buf)
    buf.seek(0)
    reader = csv.DictReader(buf)
    assert reader.fieldnames == ex.ENTRY_FIELDS and len(list(reader)) == 3

    out_path = Path(tempfile.mkdtemp()) / "out.csv"
    assert ex.main(["--out", str(out_path)]) == 0
    assert out_path.exists()


def _test_calibrate() -> None:
    store = fresh_store()
    from data.categories import CATEGORIES
    import data.calibrate as cal
    import agent.evaluate as ev

    ref_path = Path(tempfile.mkdtemp()) / "ref.json"
    ref_path.write_text(json.dumps({"countries": [
        {"name": "Germany", "year": "2024", "left_right": 0, "lib_auth": 0, "source": "test fixture"},
        {"name": "Nowhereland", "year": "2024", "left_right": 0, "lib_auth": 0, "source": "x"},
    ]}))

    rated = {c.id: {"score": 10, "evidence": "", "sources": []} for c in CATEGORIES}
    ev.evaluate_country = lambda name, year, runs=1: dict(rated)

    reference = cal.load_reference(str(ref_path))
    result = cal.measure(reference, runs=1)
    assert len(result["rows"]) == 1                     # "Nowhereland" isn't a real country -> skipped
    assert result["rows"][0]["country"] == "Germany"
    assert result["suggested_correction_lr"] == result["rows"][0]["diff_lr"]

    assert cal.main(["--reference", str(ref_path)]) == 0


def run() -> None:
    _test_export()
    _test_calibrate()
    print("test_export_calibrate: OK")


if __name__ == "__main__":
    run()
