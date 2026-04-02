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
    from core.release_impl import main as _release_main
except Exception:
    _release_main = None


def main(argv: list[str]) -> None:
    if _release_main is None:
        print("Release helper not available.")
        raise SystemExit(1)
    rc = _release_main(argv)
    raise SystemExit(rc)
