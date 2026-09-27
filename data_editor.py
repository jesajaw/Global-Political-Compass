"""
Standalone launcher -- run this (python data_editor.py from the repo root)
to open just the data editor, without the compass window.

The same editor is also reachable from inside the main app via its "Data"
button (see main.py -> ui/app.py). Both share the same data/*.json through
ui/state.py, so edits made here show up next time the main app loads data.
"""

from ui.data_editor_window.app import main

if __name__ == "__main__":
    main()
