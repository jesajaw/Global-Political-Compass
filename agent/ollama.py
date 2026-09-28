"""Minimal Ollama client (standard library only -- no `requests` needed)."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "gemma4:31b"     # one place for the model name: evaluate.py and setup_model.py both use this
TIMEOUT_SECONDS = 600    # a 31b model on local hardware can take minutes


class AgentError(Exception):
    """Anything that goes wrong while asking the model -- the message is meant to be shown to the user."""


def generate_json(prompt: str) -> str:
    """Send the prompt to Ollama in JSON mode and return the raw text of the model's answer."""
    body = json.dumps({"model": MODEL, "prompt": prompt, "format": "json", "stream": False}).encode("utf-8")
    request = urllib.request.Request(OLLAMA_URL, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8")).get("response", "")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise AgentError(f"Model '{MODEL}' not found. Install it with:  python -m agent.setup_model")
        raise AgentError(f"Ollama returned HTTP {e.code}.")
    except (urllib.error.URLError, ConnectionError, TimeoutError):
        raise AgentError("Could not reach Ollama at localhost:11434. Is it installed and running?")
