"""
Launcher -- run this (python main.py from the repo root).

The project has three areas:
  ui/     the tkinter windows (compass + data)
  agent/  the LLM that can evaluate a country for a year (Ollama)
  data/   storage (one json per country) and evaluation (average per year)
"""

from ui.app import main

if __name__ == "__main__":
    main()
