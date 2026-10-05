"""agent/verify.py (source reachability) and agent/review.py (red-team second-model pass)."""

import io
import json
import urllib.error
import urllib.request

from ._helpers import fresh_store


class _Resp:
    def __init__(self, status):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _test_verify() -> None:
    import agent.verify as v

    urllib.request.urlopen = lambda req, timeout=None: _Resp(200)
    assert v.verify_sources(["https://real.example"]) == {"https://real.example": True}

    def fake_404(req, timeout=None):
        raise urllib.error.HTTPError(req.full_url, 404, "nf", None, io.BytesIO(b""))

    urllib.request.urlopen = fake_404
    assert v.verify_sources(["https://dead.example"]) == {"https://dead.example": False}

    def fake_405_then_ok(req, timeout=None):
        if req.get_method() == "HEAD":
            raise urllib.error.HTTPError(req.full_url, 405, "nope", None, io.BytesIO(b""))
        return _Resp(200)

    urllib.request.urlopen = fake_405_then_ok
    assert v.verify_sources(["https://head-blocked.example"]) == {"https://head-blocked.example": True}

    assert v.verify_sources(["not-a-url"]) == {"not-a-url": False}      # never touches the network
    assert v.verify_sources([]) == {}


def _test_review() -> None:
    store = fresh_store()
    from data.categories import CATEGORIES
    import agent.llm_client as lc
    import agent.review as rv

    rated = {c.id: {"score": 5, "evidence": "trust me", "sources": []} for c in CATEGORIES}
    rv.REVIEW_MODEL, rv.REVIEW_BACKEND = "some-other-model", "ollama"

    seen = {}

    def fake_generate_ollama(prompt):
        seen["model_used"] = lc.MODEL
        return json.dumps({
            "concerns": [{"category": "economy", "comment": "no real evidence", "confidence_penalty": 0.6},
                        {"category": "not_a_real_category", "comment": "ignored", "confidence_penalty": 1.0}],
            "notes": "Mostly unsupported assertions.",
        })

    lc._generate_ollama = fake_generate_ollama
    lc.MODEL = "main-model"

    result = rv.review("Germany", "2024", rated)
    assert lc.MODEL == "main-model"                                  # restored after the call
    assert seen["model_used"] == "some-other-model"                  # review used its OWN model, not the main one
    assert len(result["concerns"]) == 1 and result["concerns"][0]["category"] == "economy"

    adjusted, notes = rv.apply_review(rated, result)
    assert adjusted["economy"]["confidence"] == 0.4
    assert "confidence" not in adjusted["migration"]                 # untouched category
    assert adjusted["economy"]["score"] == 5                         # scores are never touched, only confidence
    assert "no real evidence" in notes and "Mostly unsupported" in notes

    lc._generate_ollama = lambda p: "not json"
    try:
        rv.review("Germany", "2024", rated)
        raise AssertionError("should have failed")
    except lc.AgentError:
        pass


def run() -> None:
    _test_verify()
    _test_review()
    print("test_verify_review: OK")


if __name__ == "__main__":
    run()
