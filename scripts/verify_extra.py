#!/usr/bin/env python3
"""verify_extra.py — Additional repo checks (linters / static analyzers).

Runs available tools (non-destructively) and reports results. Tools checked:
- `ruff` (Python linter/formatter)
- `mypy` (optional static typing checks)
- `cppcheck` (C/C++ static analysis)

If a tool is not installed the script prints an installation suggestion and
continues. The script exits with code 0 when no installed tool reported
problems; exits with 1 if any installed tool reported issues.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent


def run(cmd: list[str], cwd: Path = ROOT) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        return p.returncode, p.stdout or ""
    except FileNotFoundError:
        return 127, ""


def check_ruff() -> tuple[bool, str]:
    """Run ruff if available. Return (passed, output)."""
    if shutil.which("ruff") is None:
        return True, "ruff not installed; skip. Install: python3 -m pip install ruff"
    # Run ruff on Python source dirs only to avoid vendor/build noise
    targets = ["scripts", "tests", "extension/src"]
    args = [t for t in targets if (ROOT / t).exists()]
    if not args:
        return True, "No target directories for ruff found"
    cmd = ["ruff", "check", "--format", "default"] + args
    rc, out = run(cmd)
    return (rc == 0), out


def check_mypy() -> tuple[bool, str]:
    if shutil.which("mypy") is None:
        return True, "mypy not installed; skip. Install: python3 -m pip install mypy"
    # Use ignore-missing-imports to be tolerant in mixed projects
    cmd = ["mypy", "scripts", "--ignore-missing-imports"]
    rc, out = run(cmd)
    return (rc == 0), out


def check_cppcheck() -> tuple[bool, str]:
    if shutil.which("cppcheck") is None:
        return True, "cppcheck not installed; skip. Install (Ubuntu): sudo apt install cppcheck"
    # Run a focused cppcheck on libs/ if present
    target = ROOT / "libs"
    if not target.exists():
        return True, "No 'libs/' directory found to run cppcheck against"
    cmd = [
        "cppcheck",
        "--enable=warning,style,portability,information",
        "--quiet",
        "--inline-suppr",
        str(target),
    ]
    rc, out = run(cmd)
    return (rc == 0), out


def main() -> int:
    start = datetime.now()
    print("Running extra repository checks — this may take a moment.\n")

    checks = [
        ("ruff (python linter)", check_ruff),
        ("mypy (type checks)", check_mypy),
        ("cppcheck (C/C++ static analysis)", check_cppcheck),
    ]

    overall_ok = True
    results = []
    for name, fn in checks:
        print(f"-- {name} --")
        ok, out = fn()
        if out:
            # Print a concise prefix of output when long
            snippet = out.strip()
            if len(snippet) > 800:
                snippet = snippet[:800] + "\n... (truncated)"
            print(snippet)
        else:
            print("(no output)")
        print("\n")
        results.append((name, ok))
        if not ok:
            overall_ok = False

    elapsed = datetime.now() - start
    print("Summary:")
    for n, ok in results:
        print(f" - {n}: {'OK' if ok else 'ISSUES'}")

    print(f"Elapsed: {elapsed.total_seconds():.1f}s")
    if overall_ok:
        print("All installed extra checks passed.")
        return 0
    else:
        print("One or more installed checks reported issues.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
