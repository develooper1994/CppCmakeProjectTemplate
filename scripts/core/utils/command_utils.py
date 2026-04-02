"""
core/utils/command_utils.py — Shared command infrastructure utilities.

Consolidates the _wrap() error handler pattern and common argparse argument
registration previously duplicated across sol.py, lib.py, and session.py.
"""

from __future__ import annotations

import argparse
from typing import Any, Callable

from core.utils.common import CLIResult, GlobalConfig


def wrap_command(fn: Callable[..., Any], args: Any) -> CLIResult:
    """Execute a command function, catching SystemExit and returning a CLIResult.

    This is the common error-handling wrapper used by all CLI command dispatchers.
    """
    try:
        fn(args)
        return CLIResult(success=True)
    except SystemExit as e:
        return CLIResult(success=(e.code == 0), code=e.code or 1)


def add_common_args(parser: argparse.ArgumentParser) -> None:
    """Add common CLI flags (--dry-run, --yes, --json, --verbose) to a parser."""
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview changes without applying")
    parser.add_argument("--yes", "-y", action="store_true",
                        help="Skip confirmation prompts")
    parser.add_argument("--json", action="store_true",
                        help="Output results as JSON")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Enable verbose/debug output")


def apply_global_args(args: Any) -> None:
    """Apply parsed common args to GlobalConfig."""
    if hasattr(args, "dry_run") and args.dry_run:
        GlobalConfig.DRY_RUN = True
    if hasattr(args, "yes") and args.yes:
        GlobalConfig.YES = True
    if hasattr(args, "json") and args.json:
        GlobalConfig.JSON = True
    if hasattr(args, "verbose") and args.verbose:
        GlobalConfig.VERBOSE = True
