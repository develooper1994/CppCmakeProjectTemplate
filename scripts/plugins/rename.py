#!/usr/bin/env python3
"""
plugins/rename.py — Project rename plugin.

Usage: tool rename --name MyProject [--old-name CppCmakeProjectTemplate]
Delegates to scripts/core/init_impl.py — no subprocess.
"""
from __future__ import annotations

PLUGIN_META = {
    "name": "rename",
    "description": "Rename the project after cloning (adjusts files and metadata).",
    "args": [
        {"name": "name", "help": "New project name", "type": "string", "required": True},
        {"name": "old_name", "help": "Old project directory/name (optional)", "type": "string", "required": False},
    ],
}

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import core.init_impl as _impl  # scripts/core/init_impl.py


def main(argv: list[str]) -> None:
    old_argv = sys.argv
    sys.argv = ["tool rename"] + argv
    try:
        _impl.main()
    finally:
        sys.argv = old_argv
