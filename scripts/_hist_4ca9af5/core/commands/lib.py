#!/usr/bin/env python3
"""
core/commands/lib.py — Library management façade.

Imports functions directly from scripts/toollib.py — no subprocess.
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
import toollib as _lib  # scripts/toollib.py

from core.utils.common import Logger, GlobalConfig, CLIResult


# ── Thin wrappers ─────────────────────────────────────────────────────────────

def _wrap(fn, args) -> CLIResult:
    """Run a toollib cmd_* function, catch SystemExit."""
    try:
        fn(args)
        return CLIResult(success=True)
    except SystemExit as e:
        return CLIResult(success=(e.code == 0), code=e.code or 1)


def cmd_list(args):     return _wrap(_lib.cmd_list,   args)
def cmd_tree(args):     return _wrap(_lib.cmd_tree,   args)
def cmd_doctor(args):   return _wrap(_lib.cmd_doctor, args)
def cmd_add(args):      return _wrap(_lib.cmd_add,    args)
def cmd_remove(args):   return _wrap(_lib.cmd_remove, args)
def cmd_rename(args):   return _wrap(_lib.cmd_rename, args)
def cmd_move(args):     return _wrap(_lib.cmd_move,   args)
def cmd_deps(args):     return _wrap(_lib.cmd_deps,   args)
def cmd_info(args):     return _wrap(_lib.cmd_info,   args)
def cmd_test(args):     return _wrap(_lib.cmd_test,   args)
def cmd_export(args):   return _wrap(_lib.cmd_export, args)


# ── Parser (mirrors scripts/toollib.py build_parser) ─────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tool lib",
        description="Library management (add/remove/rename/move/deps/info/test/export)",
    )
    sub = parser.add_subparsers(dest="subcommand", required=True)

    # add
    p = sub.add_parser("add", help="Create a new library skeleton")
    p.add_argument("name")
    p.add_argument("--version",   default="1.0.0")
    p.add_argument("--namespace", default=None)
    p.add_argument("--deps",      default="")
    p.add_argument("--cxx-standard", default="", dest="cxx_standard")
    p.add_argument("--link-app",  action="store_true")
    p.add_argument("--dry-run",   action="store_true")
    type_grp = p.add_mutually_exclusive_group()
    type_grp.add_argument("--header-only", action="store_true", dest="header_only")
    type_grp.add_argument("--interface",   action="store_true")
    p.add_argument("--template", default="",
                   choices=["", "singleton", "pimpl", "observer", "factory"])
    p.set_defaults(func=cmd_add)

    # export
    p = sub.add_parser("export", help="Add find_package-compatible install/export rules")
    p.add_argument("name")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_export)

    # remove
    p = sub.add_parser("remove", help="Detach or delete a library")
    p.add_argument("name")
    p.add_argument("--delete",  action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_remove)

    # rename
    p = sub.add_parser("rename", help="Rename a library")
    p.add_argument("old")
    p.add_argument("new")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_rename)

    # move
    p = sub.add_parser("move", help="Move library to new location")
    p.add_argument("name")
    p.add_argument("dest")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_move)

    # deps
    p = sub.add_parser("deps", help="Add/remove local deps or add external URL deps")
    p.add_argument("name")
    p.add_argument("--add",     default="")
    p.add_argument("--remove",  default="")
    p.add_argument("--add-url", default="", dest="add_url")
    p.add_argument("--via",     default="fetchcontent",
                   choices=["fetchcontent", "vcpkg", "conan"])
    p.add_argument("--target",  default="")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_deps)

    # info
    p = sub.add_parser("info", help="Show detailed info about a library")
    p.add_argument("name")
    p.set_defaults(func=cmd_info)

    # test
    p = sub.add_parser("test", help="Build and run tests for a single library")
    p.add_argument("name")
    p.add_argument("--preset", default=None)
    p.set_defaults(func=cmd_test)

    # list
    sub.add_parser("list",   help="List all libraries").set_defaults(func=cmd_list)
    # tree
    sub.add_parser("tree",   help="ASCII dependency tree").set_defaults(func=cmd_tree)
    # doctor
    sub.add_parser("doctor", help="Check project consistency").set_defaults(func=cmd_doctor)

    return parser


def main(argv: list[str]) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if hasattr(args, "func"):
        args.func(args).exit()
    else:
        parser.print_help()
