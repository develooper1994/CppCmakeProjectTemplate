"""Helpers for the TUI moved into package space.

These helpers centralize invoking `scripts/tool.py`, reading presets, and
interacting with plugins. They use the canonical `run_capture` from
`scripts.core.utils.common` where available.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import List, Optional, Tuple, Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TOOL_SCRIPT = PROJECT_ROOT / "scripts" / "tool.py"
TOOL_CMD_BASE = [sys.executable, str(TOOL_SCRIPT)]

DEFAULT_PRESET = "gcc-debug-static-x86_64"


def _get_run_capture():
    try:
        from scripts.core.utils.common import run_capture
    except Exception:
        from core.utils.common import run_capture

    return run_capture


def run_tool_cmd(args_list: List[str]) -> Tuple[str, int]:
    run_capture = _get_run_capture()
    return run_capture(TOOL_CMD_BASE + args_list, cwd=PROJECT_ROOT, strip_ansi=True)


def initial_preset(cli_arg: Optional[str]) -> str:
    if cli_arg:
        return cli_arg
    out, rc = run_tool_cmd(["session", "load", "--print"])
    if rc == 0 and out:
        try:
            sess = json.loads(out)
            return sess.get("last_preset", DEFAULT_PRESET)
        except Exception:
            pass
    return DEFAULT_PRESET


def read_presets() -> List[Tuple[str, str]]:
    presets_file = PROJECT_ROOT / "CMakePresets.json"
    names: List[Tuple[str, str]] = []
    try:
        if presets_file.exists():
            raw = presets_file.read_text(encoding="utf-8")
            data = json.loads(raw)
            bp = data.get("buildPresets") or []
            if isinstance(bp, list):
                for entry in bp:
                    if isinstance(entry, dict):
                        nm = entry.get("name")
                        if nm:
                            label = entry.get("displayName") or nm
                            names.append((label, nm))
    except Exception:
        names = []

    if not names:
        fallback = [
            "gcc-debug-static-x86_64",
            "gcc-release-static-x86_64",
            "clang-debug-static-x86_64",
            "clang-release-static-x86_64",
            "msvc-debug-static-x64",
            "msvc-release-static-x64",
        ]
        names = [(n, n) for n in fallback]

    return names


def plugins_list() -> List[str]:
    out, rc = run_tool_cmd(["plugins", "list", "--json"])
    try:
        if rc == 0 and out:
            return json.loads(out)
    except Exception:
        pass

    out2, rc2 = run_tool_cmd(["plugins", "list"])
    if rc2 == 0 and out2:
        return [l.strip() for l in out2.splitlines() if l.strip() and not l.startswith("(")]
    return []


def plugins_describe(plugin: str) -> Tuple[Optional[Any], str, int]:
    out, rc = run_tool_cmd(["plugins", "describe", plugin])
    if rc == 0 and out:
        try:
            return (json.loads(out), out, rc)
        except Exception:
            return (None, out, rc)
    return (None, out, rc)
