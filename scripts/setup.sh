import subprocess
import sys

MODEL_NAME = "deepseek-r1:8b"  # Oder deepseek-r1:14b / llama3.3


def setup():
    print(f"Lade das Modell {MODEL_NAME} über Ollama herunter...")
    try:
        # Führt 'ollama pull deepseek-r1:8b' im Terminal aus
        subprocess.run(["ollama", "pull", MODEL_NAME], check=True)
        print("Setup erfolgreich! Das Modell ist einsatzbereit.")
    except FileNotFoundError:
        print(
            "Fehler: Ollama ist nicht installiert. Bitte installiere Ollama von https://ollama.com"
        )
        sys.exit(1)
    except subprocess.CalledProcessError:
        print("Fehler beim Herunterladen des Modells.")


if __name__ == "__main__":
    setup()