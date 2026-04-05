#!/usr/bin/env python3
"""
scripts/plugins/hooks/cmake_format_stage.py

Format staged CMake files (CMakeLists.txt and *.cmake) and re-stage them.
Intended to be used as a pre-commit `repo: local` entry or run directly for testing.

Usage:
  python3 scripts/plugins/hooks/cmake_format_stage.py [files...]

If files are provided on the command line they will be used; otherwise the
script inspects the index for staged files and formats those.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from shutil import which


def get_staged_files() -> list[str]:
    try:
        p = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return []
    if p.returncode != 0:
        return []
    return [ln.strip() for ln in p.stdout.splitlines() if ln.strip()]


def main(argv: list[str] | None = None) -> int:
    args = argv or sys.argv[1:]
    files = args
    if not files:
        files = get_staged_files()

    if not files:
        print("No staged files found; nothing to format.")
        return 0

    cmf = which("cmake-format")
    if not cmf:
        print("ERROR: `cmake-format` not found on PATH. Install it and retry.", file=sys.stderr)
        return 2

    formatted: list[str] = []
    for f in files:
        p = Path(f)
        if not p.exists():
            continue
        if p.name != "CMakeLists.txt" and p.suffix != ".cmake":
            continue

        # Run cmake-format in-place
        proc = subprocess.run([cmf, "-i", "--line-width", "100", str(p)], capture_output=True, text=True)
        if proc.returncode != 0:
            print(f"ERROR: cmake-format failed for {p}: {proc.stderr.strip()}", file=sys.stderr)
            return 3

        # Stage the possibly-updated file
        add = subprocess.run(["git", "add", str(p)], capture_output=True, text=True)
        if add.returncode != 0:
            print(f"ERROR: git add failed for {p}: {add.stderr.strip()}", file=sys.stderr)
            return 4

        formatted.append(str(p))

    if formatted:
        print("Formatted and staged files:")
        for x in formatted:
            print(" -", x)
    else:
        print("No CMake files were formatted.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
