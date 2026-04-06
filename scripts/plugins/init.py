#!/usr/bin/env python3
"""
plugins/init.py — Project rename plugin.

Usage: tool init --name MyProject [--old-name CppCmakeProjectTemplate]
Delegates to scripts/init_project.py — no subprocess.
"""
from __future__ import annotations

PLUGIN_META = {
    "name": "init",
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

import plugins.rename as _mod  # delegate to new rename plugin


def main(argv: list[str]) -> None:
    old_argv = sys.argv
    try:
        _mod.main(argv)
    finally:
        sys.argv = old_argv
