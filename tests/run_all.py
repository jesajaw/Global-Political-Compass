"""Run every test module:  python -m tests.run_all"""

import importlib
import sys
import traceback

MODULES = [
    "tests.test_store",
    "tests.test_categories",
    "tests.test_agent",
    "tests.test_llm_client",
    "tests.test_verify_review",
    "tests.test_export_calibrate",
    "tests.test_ui",
]


def main() -> int:
    failed = []
    for name in MODULES:
        try:
            importlib.import_module(name).run()
        except Exception:
            failed.append(name)
            print(f"\n{name}: FAILED", file=sys.stderr)
            traceback.print_exc()
            print()

    total = len(MODULES)
    print(f"\n{total - len(failed)}/{total} test modules passed.")
    if failed:
        print("Failed: " + ", ".join(failed), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
