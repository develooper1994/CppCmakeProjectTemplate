"""
core/commands/validate.py — tool.toml validation command
=========================================================

Usage::

    tool validate              # validate tool.toml
    tool validate --json       # JSON output
    tool validate path/to.toml # validate a specific file
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from core.utils.common import Logger, GlobalConfig


def main(argv: list[str] | None = None) -> None:
    argv = argv or []

    # Simple arg parsing — optional positional path
    toml_path: Path | None = None
    for arg in argv:
        if arg in ("--help", "-h"):
            print(__doc__)
            sys.exit(0)
        if not arg.startswith("-"):
            toml_path = Path(arg)

    from core.utils.config_schema import validate_file, validate_config
    from core.utils.config_loader import load_tool_config

    cfg = load_tool_config(toml_path)
    errors, warnings = validate_config(cfg)

    if GlobalConfig.JSON:
        print(json.dumps({"errors": errors, "warnings": warnings}, indent=2))
    else:
        for w in warnings:
            Logger.warn(w)
        for e in errors:
            Logger.error(e)
        if not errors and not warnings:
            Logger.info("tool.toml is valid — no issues found")
        elif errors:
            Logger.error(f"{len(errors)} error(s), {len(warnings)} warning(s)")
        else:
            Logger.info(f"0 errors, {len(warnings)} warning(s)")

    sys.exit(1 if errors else 0)
