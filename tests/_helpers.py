"""Shared setup for the test scripts: an isolated, throwaway data directory per run."""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo root, so `import data`/`agent`/`ui` work


def fresh_store():
    """Point data.store at a fresh temp folder so tests never touch your real data/countries/.

    Also drops store's in-memory cache (reload()) -- needed because Python caches the `data.store`
    module itself, so running several test modules in one process (tests/run_all.py) would
    otherwise leak entries from an earlier module's temp folder into this one.
    """
    from data import store
    store.COUNTRY_DIR = Path(tempfile.mkdtemp()) / "countries"
    store.reload()
    return store
