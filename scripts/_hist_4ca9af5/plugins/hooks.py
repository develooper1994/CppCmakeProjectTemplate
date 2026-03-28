#!/usr/bin/env python3
"""
plugins/hooks.py — Git pre-commit hook installer plugin.

Usage: tool hooks
Delegates to scripts/setup_hooks.py — no subprocess.
"""
from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import setup_hooks as _impl  # scripts/setup_hooks.py


def main(argv: list[str]) -> None:
    _impl.main()
