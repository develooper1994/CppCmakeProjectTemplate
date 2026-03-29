#!/usr/bin/env python3
"""core/commands/release.py — `tool release` wrapper.

Delegates to `scripts/release.py` so the unified `tool.py` dispatcher
can run the release helper as a subcommand: `tool release ...`.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure the top-level `scripts/` path is importable (consistent with other
# core commands which manipulate sys.path similarly).
_SCRIPTS = Path(__file__).resolve().parent.parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

try:
    # Prefer importing the top-level `release` module (scripts/ is on sys.path)
    import release as _release  # type: ignore
except Exception:
    try:
        # Fallback: import as part of the `scripts` package if available
        from scripts import release as _release  # type: ignore
    except Exception:
        _release = None


def main(argv: list[str]) -> None:
    if _release is None:
        print("Release helper not available.")
        raise SystemExit(1)
    # Delegate to the existing scripts/release.py main
    rc = _release.main(argv)
    raise SystemExit(rc)
