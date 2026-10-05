"""
Prepare the agent to run:  python -m agent.setup_model

Only relevant for the local Ollama backend (AGENT_BACKEND unset or "ollama") -- it pulls
AGENT_MODEL (default llama3.3:70b) via `ollama pull`. If you're on AGENT_BACKEND=api, there is
nothing to install: just set AGENT_API_BASE_URL / AGENT_API_KEY / AGENT_MODEL and you're done
(see agent/llm_client.py's docstring and agent/set_backend.example.ps1).
"""

import subprocess
import sys

from .llm_client import BACKEND, MODEL


def setup() -> None:
    if BACKEND != "ollama":
        print(f"AGENT_BACKEND={BACKEND!r} -- nothing to install locally. "
             "Make sure AGENT_API_BASE_URL, AGENT_API_KEY and AGENT_MODEL are set instead.")
        return
    if not MODEL:
        sys.exit("AGENT_MODEL is empty -- nothing to pull.")
    print(f"Pulling model {MODEL} via Ollama ... (this can be tens of GB, check disk space first)")
    try:
        subprocess.run(["ollama", "pull", MODEL], check=True)
        print("Setup finished. The model is ready.")
    except FileNotFoundError:
        sys.exit("Ollama is not installed. Get it from https://ollama.com")
    except subprocess.CalledProcessError:
        sys.exit(f"Downloading '{MODEL}' failed -- if your machine can't fit it, either pick a "
                 "smaller AGENT_MODEL or switch AGENT_BACKEND=api. See agent/llm_client.py.")


if __name__ == "__main__":
    setup()
