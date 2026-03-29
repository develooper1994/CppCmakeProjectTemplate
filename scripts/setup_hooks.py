#!/usr/bin/env python3
"""setup_hooks.py — Minimal git hook installer helper.

The full project may include a `.githooks/` or `hooks/` directory with
hook scripts. This helper copies executable hook files into `.git/hooks/`.
If no hook sources are present the script prints guidance instead.

Usage:
  python3 scripts/setup_hooks.py [--install]
"""
from __future__ import annotations

import argparse
import shutil
import stat
import sys
from pathlib import Path


def find_hook_sources(root: Path) -> list[Path]:
    # Look for common locations that might hold hook templates
    candidates = [root / "hooks", root / ".githooks", root / "scripts" / "hooks"]
    out = []
    for c in candidates:
        if c.exists() and c.is_dir():
            for p in sorted(c.iterdir()):
                if p.is_file():
                    out.append(p)
    return out


def install_hooks(sources: list[Path], git_hooks_dir: Path) -> int:
    git_hooks_dir.mkdir(parents=True, exist_ok=True)
    for src in sources:
        dest = git_hooks_dir / src.name
        shutil.copy2(src, dest)
        # Ensure the hook is executable
        dest.chmod(dest.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        print(f"Installed hook: {dest}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="setup_hooks")
    parser.add_argument("--install", action="store_true", help="Copy available hooks into .git/hooks/")
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    root = Path(__file__).resolve().parent.parent
    sources = find_hook_sources(root)
    if not sources:
        print("No hook templates found. Create a 'hooks/' or '.githooks/' directory with executable hook scripts to install.")
        print("Example: hooks/pre-commit (make it executable)")
        return 0

    if not args.install:
        print("Found hook templates:")
        for s in sources:
            print(f" - {s}")
        print("Run with --install to copy them into .git/hooks/")
        return 0

    # Install into repository .git/hooks
    git_dir = Path(".git")
    if not git_dir.exists():
        print("No .git directory found — make sure you're in a git repo before installing hooks.")
        return 1

    hooks_dir = git_dir / "hooks"
    return install_hooks(sources, hooks_dir)


if __name__ == "__main__":
    raise SystemExit(main())
