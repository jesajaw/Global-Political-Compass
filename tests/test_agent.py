"""Agent parsing/merging logic: prompt building, JSON parsing, self-consistency merge, storing."""

from ._helpers import fresh_store
import json


def run() -> None:
    store = fresh_store()
    from data.categories import CATEGORIES
    from agent.evaluate import parse, evaluate_country, store_result, _build_prompt
    from agent.llm_client import AgentError
    import agent.evaluate as ev

    # the prompt mentions every category id
    prompt = _build_prompt("Germany", "2024")
    for c in CATEGORIES:
        assert f'"{c.id}"' in prompt

    # parse: full / partial / out-of-range / prose-wrapped / malformed
    full = {c.id: {"score": 3, "evidence": "e", "sources": ["https://x"]} for c in CATEGORIES}
    rated = parse(json.dumps(full))
    assert len(rated) == 10 and rated["economy"]["score"] == 3

    partial = parse(json.dumps({"economy": {"score": 7}, "migration": {"score": -2}}))
    assert set(partial) == {"economy", "migration"}

    assert parse(json.dumps({"economy": {"score": 999}}))["economy"]["score"] == 10   # clamped
    assert "economy" in parse("Sure, here you go: " + json.dumps(full) + " hope that helps")

    for bad in ["nope", json.dumps({"economy": {"score": "x"}}), json.dumps({"unrelated": 1})]:
        try:
            parse(bad)
            raise AssertionError(f"should have failed: {bad}")
        except AgentError:
            pass

    # self-consistency: median per category across N runs, missing-in-some-runs still usable
    calls = iter([
        json.dumps({"economy": {"score": 2}, "migration": {"score": 5}}),
        json.dumps({"economy": {"score": 8}, "migration": {"score": 5}}),
        json.dumps({"economy": {"score": 5}}),
    ])
    ev.generate_json = lambda prompt: next(calls)
    merged = evaluate_country("Germany", "2024", runs=3)
    assert merged["economy"]["score"] == 5 and merged["migration"]["score"] == 5

    # store_result: origin "ai", model recorded, sources deduped
    entry = store_result(63, "2024", rated)
    assert entry.origin == "ai" and entry.model and entry.sources == ["https://x"]

    # a failing model call raises AgentError, not a crash
    ev.generate_json = lambda prompt: (_ for _ in ()).throw(AgentError("down"))
    try:
        evaluate_country("Germany", "2024")
        raise AssertionError("should have failed")
    except AgentError as e:
        assert str(e) == "down"

    print("test_agent: OK")


if __name__ == "__main__":
    run()
