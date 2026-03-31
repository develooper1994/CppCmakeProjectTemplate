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

    Logger.info(f"Running clang-tidy --fix on {len(sources)} files (this may take a while)")
    # Run clang-tidy per-file to avoid CLI length limits; run in best-effort mode
    for src in sources:
        try:
            run_proc(["clang-tidy", "-p", str(build_dir), "-fix", src])
        except SystemExit:
            Logger.warn(f"clang-tidy reported issues on {src}; continuing")

    Logger.success("clang-tidy --fix pass complete. Review changes and commit as appropriate.")


def format_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tool format", description="Formatting and automated fixes")
    sub = parser.add_subparsers(dest="subcommand")
    p = sub.add_parser("tidy-fix", help="Run clang-tidy -fix across the project")
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
