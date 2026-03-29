#!/usr/bin/env python3
"""
tui.py — lightweight launcher for the TUI.

This file contains a minimal CLI entrypoint that lazily imports the
heavy TUI implementation in `tui_ui.py`. Keeping imports light avoids
pulling `textual` at import-time.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure local scripts directory is on sys.path so local package imports
# like `core.*` resolve when executed directly (`python3 scripts/tui.py`).
_SCRIPTS = Path(__file__).resolve().parent
_PROJECT = _SCRIPTS.parent
# Ensure repository root is on sys.path so `import scripts.tui` works
# when this file is run directly as a script (`python3 scripts/tui.py`).
if str(_PROJECT) not in sys.path:
    sys.path.insert(0, str(_PROJECT))

# Import the helper from the package submodule to avoid importing this
# launcher module (`scripts/tui.py`) as `scripts.tui` which causes
# circular/self imports when executed directly.
from scripts.tui.helpers import initial_preset as _initial_preset_helper


def _initial_preset(cli_arg: str | None) -> str:
    return _initial_preset_helper(cli_arg)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="tui",
        description="Terminal UI (interactive > cli args > session > default)",
    )
    parser.add_argument(
        "--preset", default=None,
        help="Initial build preset (overrides session, overridden by interactive selection)",
    )
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    initial = _initial_preset(args.preset)

    # Lazy import the heavy UI implementation only when running the app.
    # Import the UI class from the package submodule to avoid accidental
    # self-import of this launcher module.
    from scripts.tui.ui import CppTemplateTUI

    CppTemplateTUI(initial_preset=initial).run()


if __name__ == "__main__":
    main()
