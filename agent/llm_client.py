"""
Talks to whichever LLM backend is configured -- local Ollama by default, or any hosted,
OpenAI-compatible Chat Completions API (OpenAI, xAI/Grok, Groq Cloud, Together, Fireworks,
OpenRouter, ...). evaluate.py only ever calls generate_json(); it doesn't know or care which
one answered.

Why a hosted option exists: Llama 3.3 70B needs roughly 40+ GB of RAM/VRAM even at 4-bit
quantization -- far more than a typical laptop or a single consumer GPU (a 24 GB card like a
4090 is not enough by itself). If you don't have workstation-class hardware or a 64GB+ Apple
Silicon Mac, switching to a hosted provider is one environment variable, not a code change.

Configure entirely via environment variables (nothing is hardcoded, so no key ever ends up in
the repo -- set these in your shell, your PowerShell profile, or a .ps1 you keep out of git):

    AGENT_BACKEND           "ollama" (default) or "api"

    -- ollama backend (local, free, needs the hardware above) --
    OLLAMA_URL               default http://localhost:11434/api/generate
    AGENT_MODEL               default "llama3.3:70b" -- see the note in evaluate.py's PROMPT
                              docstring / the old MODEL comment history for why. If your hardware
                              can't fit that, point this at something that does, e.g. "llama3.1:8b"
                              (~5-6 GB) -- untested here for political lean, treat it as a fallback,
                              not an equivalent swap.

    -- api backend (any OpenAI-compatible provider) --
    AGENT_API_BASE_URL        e.g. https://api.x.ai/v1              (xAI, model family "Grok")
                                    https://api.groq.com/openai/v1   (Groq Cloud, hosts Llama 3.3 70B --
                                                                       note this is a DIFFERENT company
                                                                       from xAI's "Grok", similar name only)
                                    https://api.openai.com/v1        (OpenAI)
    AGENT_API_KEY              your API key for that provider
    AGENT_MODEL                the provider's model id, e.g. "grok-4.5", "llama-3.3-70b-versatile", "gpt-4o"

See agent/set_backend.example.ps1 for ready-to-edit examples of both.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

BACKEND = os.environ.get("AGENT_BACKEND", "ollama").strip().lower()
MODEL = os.environ.get("AGENT_MODEL", "llama3.3:70b" if BACKEND == "ollama" else "")

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/generate")
API_BASE_URL = os.environ.get("AGENT_API_BASE_URL", "")
API_KEY = os.environ.get("AGENT_API_KEY", "")
TIMEOUT_SECONDS = int(os.environ.get("AGENT_TIMEOUT_SECONDS", "600"))


class AgentError(Exception):
    """Anything that goes wrong while asking the model -- the message is meant to be shown to the user."""


def generate_json(prompt: str) -> str:
    """Send the prompt to whichever backend is configured; returns the raw text of the model's answer."""
    if BACKEND == "api":
        return _generate_api(prompt)
    if BACKEND == "ollama":
        return _generate_ollama(prompt)
    raise AgentError(f'Unknown AGENT_BACKEND "{BACKEND}" -- use "ollama" or "api".')


# -- local Ollama -------------------------------------------------------------------------------

def _generate_ollama(prompt: str) -> str:
    if not MODEL:
        raise AgentError("No AGENT_MODEL configured for the ollama backend.")
    body = json.dumps({"model": MODEL, "prompt": prompt, "format": "json", "stream": False}).encode("utf-8")
    request = urllib.request.Request(OLLAMA_URL, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8")).get("response", "")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise AgentError(f"Model '{MODEL}' not found locally. Install it with:  python -m agent.setup_model")
        raise AgentError(f"Ollama returned HTTP {e.code}.")
    except (urllib.error.URLError, ConnectionError, TimeoutError):
        raise AgentError(
            f"Could not reach Ollama at {OLLAMA_URL}. Is it installed and running? "
            "(No suitable hardware? Set AGENT_BACKEND=api to use a hosted provider instead -- "
            "see agent/llm_client.py's docstring.)"
        )


# -- hosted, OpenAI-compatible API ---------------------------------------------------------------

def _generate_api(prompt: str, *, _retry_without_json_mode: bool = True) -> str:
    if not (API_BASE_URL and API_KEY and MODEL):
        raise AgentError("AGENT_BACKEND=api needs AGENT_API_BASE_URL, AGENT_API_KEY and AGENT_MODEL all set.")
    payload = {"model": MODEL, "messages": [{"role": "user", "content": prompt}]}
    if _retry_without_json_mode:
        payload["response_format"] = {"type": "json_object"}   # not every provider supports this; retried without it below

    url = API_BASE_URL.rstrip("/") + "/chat/completions"
    request = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={
        "Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}",
    })
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:300]
        if e.code == 400 and _retry_without_json_mode:      # some providers reject response_format -- try once without it
            return _generate_api(prompt, _retry_without_json_mode=False)
        if e.code == 401:
            raise AgentError("The API rejected the key (HTTP 401). Check AGENT_API_KEY.")
        raise AgentError(f"The API returned HTTP {e.code}: {detail}")
    except (urllib.error.URLError, ConnectionError, TimeoutError):
        raise AgentError(f"Could not reach {API_BASE_URL}.")

    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise AgentError("The API's response didn't have the expected shape (choices[0].message.content).")
