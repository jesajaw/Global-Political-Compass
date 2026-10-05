"""Storage layer: countries.json, per-country files, categories, origin promotion, validation."""

from ._helpers import fresh_store


def run() -> None:
    store = fresh_store()
    from data import scoring
    from data.categories import CATEGORIES

    assert len(store.countries()) == 195
    assert store.all_years() == [] and store.countries_with_data() == []
    assert scoring.get_score(63, "2024") is None

    # plain manual entry
    e1 = store.add_entry(63, "2024", -20, -40, summary="a", sources=["https://x", " "])
    e2 = store.add_entry(63, "2024", -30, -30)
    assert e1.id.endswith("-63.1") and e2.id.endswith("-63.2")
    assert (store.COUNTRY_DIR / "63.json").exists()
    s = scoring.get_score(63, "2024")
    assert (s.left_right, s.lib_auth, s.count) == (-25, -35, 2)
    assert e1.sources == ["https://x"]              # blank source stripped

    # category-driven entry: axes computed automatically
    cats = {c.id: {"score": 5, "evidence": "e", "confidence": 0.8} for c in CATEGORIES}
    e3 = store.add_entry(64, "2024", categories=cats, origin="ai", model="llama3.3:70b")
    assert e3.origin == "ai" and e3.left_right == 50 and e3.lib_auth == 25

    # editing an "ai" entry promotes it to "manual_ai" and that sticks
    store.update_entry(64, e3.id, summary="reviewed")
    assert store.entries(64, "2024")[0].origin == "manual_ai"
    store.update_entry(64, e3.id, summary="edited again")
    assert store.entries(64, "2024")[0].origin == "manual_ai"

    # recompute_from_categories re-derives the axes from an updated breakdown
    store.update_entry(64, e3.id, categories={**cats, "economy": {"score": -10}}, recompute_from_categories=True)
    assert store.entries(64, "2024")[0].left_right < 50

    # verification / review fields round-trip through disk
    e4 = store.add_entry(65, "2024", 10, -10, sources_verified={"https://a": True}, review_notes="ok", reviewed_by="m2")
    store.reload()
    r = store.entries(65, "2024")[0]
    assert r.sources_verified == {"https://a": True} and r.review_notes == "ok" and r.reviewed_by == "m2"

    # validation
    for bad in [("20x4", 0, 0), ("2024", 101, 0), ("2024", "a", 0)]:
        try:
            store.add_entry(63, *bad)
            raise AssertionError(f"should have failed: {bad}")
        except ValueError:
            pass
    try:
        store.add_entry(9999, "2024", 0, 0)
        raise AssertionError("should have failed: unknown country")
    except KeyError:
        pass
    try:
        store.add_entry(66, "2024")                 # neither axes nor categories given
        raise AssertionError("should have failed: nothing to compute from")
    except ValueError:
        pass

    # deleting the last entry removes the country's file; a broken file is skipped, not fatal
    for e in [e1, e2]:
        store.delete_entry(63, e.id)
    assert not (store.COUNTRY_DIR / "63.json").exists()
    store.COUNTRY_DIR.mkdir(exist_ok=True)
    (store.COUNTRY_DIR / "999.json").write_text("{not valid json")
    store.reload()
    assert 999 not in store.countries_with_data()

    print("test_store: OK")


if __name__ == "__main__":
    run()
