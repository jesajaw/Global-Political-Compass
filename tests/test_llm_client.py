"""agent/llm_client.py: both backends (ollama + hosted API), error messages, json-mode fallback."""

import io
import json
import os
import urllib.error
import urllib.request

from . import _helpers  # noqa: F401  (sets up sys.path)


class _FakeResponse:
    def __init__(self, body: str):
        self._body = body.encode("utf-8")

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def run() -> None:
    import importlib
    import agent.llm_client as lc

    for key in ("AGENT_BACKEND", "AGENT_MODEL", "AGENT_API_BASE_URL", "AGENT_API_KEY"):
        os.environ.pop(key, None)
    importlib.reload(lc)
    assert lc.BACKEND == "ollama" and lc.MODEL == "llama3.3:70b"

    seen = {}

    def fake_ollama(req, timeout=None):
        seen["body"] = json.loads(req.data)
        return _FakeResponse(json.dumps({"response": '{"economy": {"score": 1}}'}))

    urllib.request.urlopen = fake_ollama
    assert lc.generate_json("hello") == '{"economy": {"score": 1}}'
    assert seen["body"]["model"] == "llama3.3:70b" and seen["body"]["format"] == "json"

    def fake_404(req, timeout=None):
        raise urllib.error.HTTPError(req.full_url, 404, "nf", None, io.BytesIO(b""))

    urllib.request.urlopen = fake_404
    try:
        lc.generate_json("x")
        raise AssertionError("should have failed")
    except lc.AgentError as e:
        assert "not found locally" in str(e)

    def fake_conn_error(req, timeout=None):
        raise ConnectionError("refused")

    urllib.request.urlopen = fake_conn_error
    try:
        lc.generate_json("x")
        raise AssertionError("should have failed")
    except lc.AgentError as e:
        assert "AGENT_BACKEND=api" in str(e)      # points at the alternative

    # -- api backend --------------------------------------------------------------------
    os.environ.update(AGENT_BACKEND="api", AGENT_API_BASE_URL="https://api.example.test/v1",
                      AGENT_API_KEY="secret", AGENT_MODEL="some-model")
    importlib.reload(lc)
    assert lc.BACKEND == "api" and lc.MODEL == "some-model"

    def fake_api(req, timeout=None):
        seen["auth"] = req.headers.get("Authorization")
        body = json.loads(req.data)
        assert body.get("response_format") == {"type": "json_object"}
        return _FakeResponse(json.dumps({"choices": [{"message": {"content": '{"economy": {"score": 2}}'}}]}))

    urllib.request.urlopen = fake_api
    assert lc.generate_json("hi") == '{"economy": {"score": 2}}'
    assert seen["auth"] == "Bearer secret"

    # provider rejects response_format (400) -> retried once without it
    calls = {"n": 0}

    def fake_400_then_ok(req, timeout=None):
        calls["n"] += 1
        body = json.loads(req.data)
        if calls["n"] == 1:
            assert "response_format" in body
            raise urllib.error.HTTPError(req.full_url, 400, "bad", None, io.BytesIO(b""))
        assert "response_format" not in body
        return _FakeResponse(json.dumps({"choices": [{"message": {"content": '{"economy": {"score": 3}}'}}]}))

    urllib.request.urlopen = fake_400_then_ok
    assert lc.generate_json("hi") == '{"economy": {"score": 3}}' and calls["n"] == 2

    def fake_401(req, timeout=None):
        raise urllib.error.HTTPError(req.full_url, 401, "unauthorized", None, io.BytesIO(b""))

    urllib.request.urlopen = fake_401
    try:
        lc.generate_json("x")
        raise AssertionError("should have failed")
    except lc.AgentError as e:
        assert "AGENT_API_KEY" in str(e)

    os.environ.pop("AGENT_API_KEY")
    importlib.reload(lc)
    try:
        lc.generate_json("x")
        raise AssertionError("should have failed")
    except lc.AgentError as e:
        assert "AGENT_API_KEY" in str(e)          # missing config caught before any network call

    for key in ("AGENT_BACKEND", "AGENT_API_BASE_URL", "AGENT_API_KEY", "AGENT_MODEL"):
        os.environ.pop(key, None)
    importlib.reload(lc)

    print("test_llm_client: OK")


if __name__ == "__main__":
    run()
