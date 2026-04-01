#!/usr/bin/env python3
"""
core/commands/format.py — Formatting and automated fix helpers

Provides `tool format tidy-fix` which runs `clang-tidy -fix` across project
source files (best-effort). Intended to be run locally and in CI to produce
fix patches which can be reviewed and applied.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from core.utils.common import Logger, PROJECT_ROOT, run_proc, CLIResult


def _impl_tidy_fix(args) -> None:
    if not shutil.which("clang-tidy"):
        Logger.error("clang-tidy not found. Install clang-tidy to run tidy-fix.")
        raise SystemExit(1)

    build_dir = PROJECT_ROOT / "build"
    if not (build_dir / "compile_commands.json").exists():
        Logger.error("compile_commands.json not found in build/; configure the project first (cmake).")
        raise SystemExit(1)

    # Gather candidate source files from common directories
    sources = []
    cand_dirs = ["libs", "apps", "tests", "gui_app", "main_app"]
    for d in cand_dirs:
        p = PROJECT_ROOT / d
        if p.exists():
            for f in p.rglob("*.cpp"):
                sources.append(str(f))

    if not sources:
        Logger.warn("No source files found for clang-tidy run")
        return

    checks_arg = None
    if getattr(args, 'checks', None):
        checks_arg = f"--checks={args.checks}"

    mode = "apply" if getattr(args, 'apply', False) else "dry-run"
    Logger.info(f"Running clang-tidy ({mode}) on {len(sources)} files")

    # Run clang-tidy per-file to avoid CLI length limits; run in best-effort mode
    for src in sources:
        cmd = ["clang-tidy", "-p", str(build_dir)]
        if checks_arg:
            cmd.append(checks_arg)
        if getattr(args, 'apply', False):
            cmd.append("-fix")
        cmd.append(src)
        try:
            run_proc(cmd)
        except SystemExit:
            Logger.warn(f"clang-tidy reported issues on {src}; continuing")

    # If apply mode, record a patch for review
    if getattr(args, 'apply', False):
        out, rc = run_proc(["git", "diff", "--no-prefix"], check=False), 0
        # run_proc returns int when check=False; capture using run_capture instead
        try:
            from core.utils.common import run_capture
            diff_out, _ = run_capture(["git", "diff", "--no-prefix"]) if shutil.which("git") else ("", 0)
            patch_path = (PROJECT_ROOT / "build" / "tidy_fix.patch")
            patch_path.parent.mkdir(parents=True, exist_ok=True)
            patch_path.write_text(diff_out + "\n", encoding="utf-8")
            if diff_out.strip():
                Logger.info(f"clang-tidy applied changes; patch written to: {patch_path}")
            else:
                Logger.info("clang-tidy applied no changes; patch empty")
        except Exception:
            Logger.warn("Failed to record git diff for tidy-fix (git may be unavailable)")

    Logger.success("clang-tidy pass complete. Review changes and commit as appropriate.")


def format_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tool format", description="Formatting and automated fixes")
    sub = parser.add_subparsers(dest="subcommand")
    p = sub.add_parser("tidy-fix", help="Run clang-tidy -fix across the project")
    p.add_argument("--dry-run", action="store_true", help="Run clang-tidy without applying fixes (default)")
    p.add_argument("--apply", action="store_true", help="Apply fixes (runs clang-tidy -fix) and record patch")
    p.add_argument("--checks", default=None, help="Pass a -checks pattern to clang-tidy (e.g. '*,-llvm-*')")
    p.set_defaults(func=lambda args: _impl_tidy_fix(args))
    return parser


def main(argv: list[str]) -> None:
    parser = format_parser()
    args = parser.parse_args(argv if argv else [])
    if hasattr(args, "func"):
        try:
            args.func(args)
        except SystemExit as e:
            raise
    else:
        parser.print_help()
