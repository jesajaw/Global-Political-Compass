"""
Launcher -- run this (python main.py from the repo root).

Everything else lives in the ui package: ui/app.py wires the pieces
together, ui/compass_window and ui/data_editor_window each own one window.
"""

from ui.app import main

if __name__ == "__main__":
    main()
