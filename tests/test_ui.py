"""
End-to-end UI logic against tests/faketk.py -- a stand-in for tkinter, not a tkinter
replacement (see tests/README.md). Drives the real ui/ code: manual entries, the agent flow
(including verify-sources / red-team review), editing, deleting, hover tooltips.
"""

import sys
import tempfile
import time
from pathlib import Path

from . import _helpers  # noqa: F401  (sets up sys.path)

sys.path.insert(0, str(Path(__file__).resolve().parent))   # so "import faketk as tkinter" style works below


def run() -> None:
    import tests.faketk as tkinter
    sys.modules["tkinter"] = tkinter

    from data import store
    store.COUNTRY_DIR = Path(tempfile.mkdtemp()) / "countries"
    store.reload()      # drop any cache left by an earlier test module in this process
    from data.categories import CATEGORIES

    from ui.compass_window import CompassWindow
    from ui.data_window.window import DataView
    import ui.dialogs as dialogs

    errors = []
    dialogs.show_error = lambda p, t, m: errors.append((t, m))
    dialogs.ask_yes_no = lambda *a: True

    root = tkinter.Tk()
    win = CompassWindow(root)
    c = win.canvas
    assert win.year_var.get() == "" and c._points == []      # empty state: nothing to plot yet

    dv = DataView(root, win.refresh)

    # -- manual entry --------------------------------------------------------------------
    dv._fill_list("germ")
    assert [x.name for x in dv._shown] == ["Germany"]
    dv.listbox.sel = (0,)
    dv._on_country_select()

    def fill(year, lr, la, summary=""):
        dv.year_entry.delete(0, "end"); dv.year_entry.insert(0, year)
        dv.lr_field.set(lr); dv.la_field.set(la)
        dv.summary_entry.delete(0, "end"); dv.summary_entry.insert(0, summary)

    fill("2024", -20, -40, "one"); dv._save()
    dv._new_entry(); fill("2024", -30, -30, "two"); dv._save()
    assert not errors, errors
    from data import scoring
    assert scoring.get_score(63, "2024").left_right == -25
    win.refresh()
    assert win.year_var.get() == "2024" and len(c._points) == 1

    kids = dv.tree.get_children("y:2024")
    assert len(kids) == 2
    dv.tree.selection_set(kids[0]); dv._on_tree_select()
    assert dv._editing_id == kids[0] and dv.lr_field._var.get() == "-20"
    dv.lr_field.set(-10); dv._save()
    assert scoring.get_score(63, "2024").left_right == -20 and store.entry_count(63) == 2

    dv._new_entry(); dv.lr_field._var.set("abc"); dv._save()
    assert errors and store.entry_count(63) == 2; errors.clear()

    dv.tree.selection_set(kids[1]); dv._on_tree_select(); dv._delete()
    assert store.entry_count(63) == 1

    # -- agent entry: verify sources + red-team review -----------------------------------
    import agent
    rated = {c.id: {"score": 5, "evidence": "e", "sources": ["https://a", "https://dead"]} for c in CATEGORIES}
    agent.evaluate_country = lambda name, year: dict(rated)
    import agent.verify as verify_mod
    verify_mod.verify_sources = lambda urls: {u: (u != "https://dead") for u in urls}
    import agent.review as review_mod
    review_mod.review = lambda name, year, r: {
        "concerns": [{"category": "economy", "comment": "thin", "confidence_penalty": 0.4}], "notes": "Check this."}
    review_mod.REVIEW_MODEL = "reviewer-x"

    dv._new_entry(); dv.year_entry.delete(0, "end"); dv.year_entry.insert(0, "2025")
    dv.verify_sources_var.set(True); dv.review_var.set(True)
    dv._evaluate()
    pending = list(tkinter._pending); tkinter._pending.clear()
    time.sleep(0.3)
    for fn in pending:
        fn()
    assert not errors, errors

    ai_entry = store.entries(63, "2025")[0]
    assert ai_entry.origin == "ai" and ai_entry.sources_verified == {"https://a": True, "https://dead": False}
    assert ai_entry.reviewed_by == "reviewer-x" and "Check this." in ai_entry.review_notes
    assert ai_entry.categories["economy"].confidence == 0.6

    kids25 = dv.tree.get_children("y:2025")
    dv.tree.selection_set(kids25[0]); dv._on_tree_select()
    label = dv.category_label.opts.get("text", "")
    assert "conf. 0.6" in label and "Sources: 1/2 reachable" in label and "Check this." in label, label

    # editing the ai entry through the form promotes it to "manual_ai"
    dv.summary_entry.delete(0, "end"); dv.summary_entry.insert(0, "reviewed by human"); dv._save()
    assert store.entries(63, "2025")[0].origin == "manual_ai"

    # -- compass hover tooltip shows categories + verification + review ------------------
    c.set_year("2025")
    p = c._points[0]

    class Ev:
        pass

    ev = Ev(); ev.x, ev.y = int(p["px"]), int(p["py"])
    c._on_motion(ev)
    tip = " | ".join(i[3].get("text", "") for i in c.items if i[3].get("tags") == "tip")
    assert "Category breakdown" in tip and "(context only)" in tip
    assert "Sources checked: 1/2 reachable" in tip and "Check this." in tip

    print("test_ui: OK")


if __name__ == "__main__":
    run()
