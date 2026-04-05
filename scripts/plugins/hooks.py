#!/usr/bin/env python3
"""
plugins/hooks.py — Git pre-commit hook installer plugin.

Usage: tool hooks [--install]
"""
from __future__ import annotations

import argparse
import shutil
import stat
from pathlib import Path
from core.utils.common import Logger, PROJECT_ROOT

PLUGIN_META = {
    "name": "hooks",
    "description": "Install git pre-commit hooks for the project.",
}


def find_hook_sources(root: Path) -> list[Path]:
    candidates = [root / "hooks", root / ".githooks", root / "scripts" / "hooks", root / "scripts" / "plugins" / "hooks"]
    out = []
    for c in candidates:
        if c.exists() and c.is_dir():
            for p in sorted(c.iterdir()):
                if p.is_file():
                    out.append(p)
    return out


def main(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(prog="tool hooks")
    parser.add_argument("--install", action="store_true", help="Copy available hooks into .git/hooks/")
    args = parser.parse_args(argv)

    sources = find_hook_sources(PROJECT_ROOT)
    if not sources:
        Logger.info("No hook templates found in hooks/, .githooks/, scripts/hooks/ or scripts/plugins/hooks/")
        return

    if not args.install:
        Logger.info("Found hook templates:")
        for s in sources:
            print(f" - {s.relative_to(PROJECT_ROOT)}")
        print("\nRun with --install to copy them into .git/hooks/")
        return

    git_dir = PROJECT_ROOT / ".git"
    if not git_dir.exists():
        Logger.error("No .git directory found; hooks can only be installed in a git repository.")
        return

    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)

    for src in sources:
        dest = hooks_dir / src.name
        shutil.copy2(src, dest)
        # Make executable
        dest.chmod(dest.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        Logger.success(f"Installed hook: {src.name}")
