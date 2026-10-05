# Tests

Plain `assert`-based scripts, standard library only (no pytest, no new dependency). Every
network and model call is faked/mocked -- these never touch Ollama, a real API, or the internet.

Run everything:

    python -m tests.run_all

Run one file directly for a shorter traceback while debugging:

    python -m tests.test_store

`tests/faketk.py` is a small stand-in for tkinter (just enough to construct the real widget
tree and record what was drawn/configured) so `test_ui.py` can exercise the actual `ui/` code
without a display or a tkinter installation. It is NOT a tkinter replacement for running the
app -- only for testing it headlessly.
