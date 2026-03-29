#!/usr/bin/env python3
"""
core/commands/session.py — Session save/load utilities for tool and TUI.

Commands:
  session save [--default-cmd "build check"]  # backup + save current settings
  session load [--print]                        # load and optionally print session
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

_SCRIPTS = Path(__file__).resolve().parent.parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from core.utils.common import (
    GlobalConfig,
    CLIResult,
    load_session,
    save_session,
    backup_session,
)


def _impl_cmd_save(args) -> None:
    sess = load_session() or {}
    # Backup existing session first
    bak = backup_session()
    if bak:
        print(f"Backed up session -> {bak}")
    # Update with current runtime flags
    sess.update({
        "verbose": bool(GlobalConfig.VERBOSE),
        "json": bool(GlobalConfig.JSON),
        "yes": bool(GlobalConfig.YES),
        "dry_run": bool(GlobalConfig.DRY_RUN),
    })
    if getattr(args, "default_cmd", None):
        sess["default_command"] = args.default_cmd
    save_session(sess)
    print("Session saved.")


def _impl_cmd_load(args) -> None:
    sess = load_session() or {}
    if getattr(args, "print", False):
        print(json.dumps(sess, indent=2, ensure_ascii=False))
        return
    # Apply to runtime globals (note: CLI flags still take precedence when present)
    GlobalConfig.VERBOSE = bool(sess.get("verbose", GlobalConfig.VERBOSE))
    GlobalConfig.JSON = bool(sess.get("json", GlobalConfig.JSON))
    GlobalConfig.YES = bool(sess.get("yes", GlobalConfig.YES))
    GlobalConfig.DRY_RUN = bool(sess.get("dry_run", GlobalConfig.DRY_RUN))
    print("Session loaded into runtime globals.")


def _impl_cmd_set(args) -> None:
    """Set a session key to a value. Value will be JSON-decoded when possible."""
    key = getattr(args, "key")
    val = getattr(args, "value")
    sess = load_session() or {}
    try:
        parsed = json.loads(val)
    except Exception:
        parsed = val
    sess[key] = parsed
    save_session(sess)
    print(f"Set session {key}")


def _wrap(fn, args) -> CLIResult:
    try:
        fn(args)
        return CLIResult(success=True)
    except SystemExit as e:
        return CLIResult(success=(e.code == 0), code=e.code or 1)


def cmd_save(args):
    return _wrap(_impl_cmd_save, args)


def cmd_load(args):
    return _wrap(_impl_cmd_load, args)


def cmd_set(args):
    return _wrap(_impl_cmd_set, args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tool session", description="Session save/load")
    sub = parser.add_subparsers(dest="action", required=True)

    p = sub.add_parser("save", help="Backup and save current session")
    p.add_argument("--default-cmd", dest="default_cmd", default=None,
                   help="Set default command to run when no CLI command provided (e.g. 'build check')")
    p.set_defaults(func=cmd_save)

    p = sub.add_parser("load", help="Load session into runtime globals")
    p.add_argument("--print", action="store_true", help="Print session JSON instead of applying")
    p.set_defaults(func=cmd_load)

    p = sub.add_parser("set", help="Set a session key to a value (value may be JSON)")
    p.add_argument("--key", required=True, help="Session key to set")
    p.add_argument("--value", required=True, help="Value to set (JSON-decoded when possible)")
    p.set_defaults(func=cmd_set)

    return parser


def main(argv: list[str]) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if hasattr(args, "func"):
        args.func(args).exit()
    else:
        parser.print_help()


if __name__ == "__main__":
    main(sys.argv[1:])
