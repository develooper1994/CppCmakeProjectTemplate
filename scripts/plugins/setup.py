#!/usr/bin/env python3
"""
plugins/setup.py — Dependency checker/installer plugin.

Usage: tool setup [--install] [--all]
Delegates to scripts/install_deps.py — no subprocess.
"""
from __future__ import annotations

PLUGIN_META = {
    "name": "setup",
    "description": "Check and optionally install system and Python dependencies for the project.",
    "args": [
        {"name": "install", "help": "Run installation of detected missing packages", "type": "flag", "required": False},
        {"name": "all", "help": "Install all optional dependencies as well", "type": "flag", "required": False},
    ],
}

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import install_deps as _impl  # scripts/install_deps.py


def main(argv: list[str]) -> None:
    # Re-use install_deps argparse-based main, passing our argv
    old_argv = sys.argv
    sys.argv = ["tool setup"] + argv
    try:
        _impl.main()
    finally:
        sys.argv = old_argv
