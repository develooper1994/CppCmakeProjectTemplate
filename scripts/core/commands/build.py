#!/usr/bin/env python3
"""
core/commands/build.py — Build command façade.

Imports functions directly from scripts/build.py — no subprocess.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# ── Path bootstrap ────────────────────────────────────────────────────────────
_SCRIPTS = Path(__file__).resolve().parent.parent.parent  # scripts/
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

# Import real implementation (no subprocess)
import build as _build  # scripts/build.py

from core.utils.common import Logger, GlobalConfig, CLIResult


# ── Thin wrappers that forward to the real implementation ─────────────────────

def cmd_build(args: argparse.Namespace) -> CLIResult:
    # Propagate dry-run / verbose into scripts/build.py's global defaults
    if GlobalConfig.DRY_RUN:
        Logger.info("[DRY-RUN] Would run: cmake --preset + cmake --build")
        return CLIResult(success=True, message="[DRY-RUN] build skipped")
    try:
        _build.cmd_build(args)
        return CLIResult(success=True, message="Build complete.")
    except SystemExit as e:
        return CLIResult(success=(e.code == 0), code=e.code or 1, message="Build failed.")


def cmd_check(args: argparse.Namespace) -> CLIResult:
    if GlobalConfig.DRY_RUN:
        Logger.info("[DRY-RUN] Would run: cmake + build + ctest + extension sync")
        return CLIResult(success=True, message="[DRY-RUN] check skipped")
    try:
        _build.cmd_check(args)
        return CLIResult(success=True, message="All checks passed.")
    except SystemExit as e:
        return CLIResult(success=(e.code == 0), code=e.code or 1, message="Check failed.")


def cmd_clean(args: argparse.Namespace) -> CLIResult:
    if GlobalConfig.DRY_RUN:
        Logger.info("[DRY-RUN] Would clean build artifacts")
        return CLIResult(success=True, message="[DRY-RUN] clean skipped")
    _build.cmd_clean(args)
    return CLIResult(success=True, message="Clean done.")


def cmd_deploy(args: argparse.Namespace) -> CLIResult:
    if GlobalConfig.DRY_RUN:
        Logger.info(f"[DRY-RUN] Would deploy to {args.host}:{args.path}")
        return CLIResult(success=True, message="[DRY-RUN] deploy skipped")
    try:
        _build.cmd_deploy(args)
        return CLIResult(success=True, message="Deploy complete.")
    except SystemExit as e:
        return CLIResult(success=(e.code == 0), code=e.code or 1, message="Deploy failed.")


def cmd_extension(args: argparse.Namespace) -> CLIResult:
    if GlobalConfig.DRY_RUN:
        Logger.info("[DRY-RUN] Would build .vsix extension")
        return CLIResult(success=True, message="[DRY-RUN] extension skipped")
    try:
        _build.cmd_extension(args)
        return CLIResult(success=True, message="Extension built.")
    except SystemExit as e:
        return CLIResult(success=(e.code == 0), code=e.code or 1, message="Extension build failed.")


# ── Parser (mirrors scripts/build.py's parser) ────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tool build",
        description="Build system automation",
    )
    sub = parser.add_subparsers(dest="subcommand")

    # build
    p = sub.add_parser("build", help="Configure + compile")
    p.add_argument("--preset", default=None)
    p.set_defaults(func=cmd_build)

    # check
    p = sub.add_parser("check", help="Build + test + extension sync")
    p.add_argument("--preset",  default=None)
    p.add_argument("--no-sync", action="store_true")
    p.set_defaults(func=cmd_check)

    # clean
    p = sub.add_parser("clean", help="Remove build artifacts")
    p.add_argument("targets", nargs="*")
    p.add_argument("--all", action="store_true")
    p.set_defaults(func=cmd_clean)

    # deploy
    p = sub.add_parser("deploy", help="Remote deploy via rsync")
    p.add_argument("--host", required=True)
    p.add_argument("--path", default="/tmp/cpp_project")
    p.add_argument("--preset", default=None)
    p.set_defaults(func=cmd_deploy)

    # extension
    p = sub.add_parser("extension", help="Build .vsix extension")
    p.add_argument("--install", action="store_true")
    p.add_argument("--publish", action="store_true")
    p.set_defaults(func=cmd_extension)

    return parser


def main(argv: list[str]) -> None:
    parser = build_parser()
    # Default subcommand: "build"
    args = parser.parse_args(argv if argv else ["build"])
    if hasattr(args, "func"):
        args.func(args).exit()
    else:
        parser.print_help()
