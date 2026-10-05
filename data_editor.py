"""
Standalone launcher (python data_editor.py from the repo root): opens just the Data window,
without the compass. Same data files as the main app -- entries added here show up the next
time the compass starts (or when it refreshes after using its own Data window).
"""

from ui.app import main_editor

if __name__ == "__main__":
    main_editor()
