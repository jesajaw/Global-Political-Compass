"""Download the model the agent uses:  python -m agent.setup_model"""

import subprocess
import sys

from .ollama import MODEL


def setup() -> None:
    print(f"Pulling model {MODEL} via Ollama ...")
    try:
        subprocess.run(["ollama", "pull", MODEL], check=True)
        print("Setup finished. The model is ready.")
    except FileNotFoundError:
        sys.exit("Ollama is not installed. Get it from https://ollama.com")
    except subprocess.CalledProcessError:
        sys.exit("Downloading the model failed.")


if __name__ == "__main__":
    setup()
