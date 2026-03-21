#!/usr/bin/env python3
"""
libtool.py — Proje kütüphane yönetim CLI aracı.

Komutlar:

    libtool add <name>
    libtool remove <name> [--delete]
    libtool rename <old> <new>
    libtool list
    libtool doctor

Amaç:
    - deterministic
    - scriptable
    - CI friendly
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from lib_manager_core import (
    LibManager,
    find_references,
    validate_name,
)


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def project_root() -> Path:
    """
    scripts/libtool.py konumundan root bulur.
    """

    return Path(__file__).resolve().parent.parent


def create_manager() -> LibManager:

    return LibManager(project_root())


def fail(msg: str) -> None:

    print(f"❌ {msg}", file=sys.stderr)

    sys.exit(1)


# ─────────────────────────────────────────────────────────────
# Commands
# ─────────────────────────────────────────────────────────────

def cmd_add(args: argparse.Namespace) -> None:

    mgr = create_manager()

    try:

        validate_name(args.name)

        mgr.add(args.name)

    except Exception as e:

        fail(str(e))

    print(f"✅ library added: {args.name}")


# ─────────────────────────────────────────────────────────────

def cmd_remove(args: argparse.Namespace) -> None:

    mgr = create_manager()

    try:

        validate_name(args.name)

        if args.dry_run:

            refs = find_references(
                project_root(),
                args.name,
            )

            if refs:

                print("References found:")

                for r in refs:
                    print("  ", r)

            else:

                print("No references.")

            return

        mgr.remove(
            args.name,
            delete=args.delete,
        )

    except Exception as e:

        fail(str(e))

    print(f"✅ library removed: {args.name}")


# ─────────────────────────────────────────────────────────────

def cmd_rename(args: argparse.Namespace) -> None:

    mgr = create_manager()

    try:

        validate_name(args.old)

        validate_name(args.new)

        mgr.rename(
            args.old,
            args.new,
        )

    except Exception as e:

        fail(str(e))

    print(f"✅ library renamed: {args.old} → {args.new}")


# ─────────────────────────────────────────────────────────────

def cmd_list(_: argparse.Namespace) -> None:

    root = project_root()

    libs_dir = root / "libs"

    if not libs_dir.exists():

        fail("libs directory not found")

    names = []

    for d in libs_dir.iterdir():

        if d.is_dir():

            names.append(d.name)

    names.sort()

    if not names:

        print("No libraries.")

        return

    print("Libraries:")

    for n in names:

        print("  ", n)


# ─────────────────────────────────────────────────────────────

def cmd_doctor(_: argparse.Namespace) -> None:

    root = project_root()

    libs_dir = root / "libs"

    if not libs_dir.exists():

        fail("libs directory missing")

    print("Running diagnostics...\n")

    issues = 0

    for lib in libs_dir.iterdir():

        if not lib.is_dir():

            continue

        name = lib.name

        refs = find_references(
            root,
            name,
        )

        if not refs:

            print(f"⚠ orphan library: {name}")

            issues += 1

    if issues == 0:

        print("✅ project healthy")

    else:

        print()

        print(f"Issues found: {issues}")

        sys.exit(1)


# ─────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:

    parser = argparse.ArgumentParser(
        prog="libtool",
        description="Library management tool",
    )

    sub = parser.add_subparsers(
        dest="command",
        required=True,
    )

    # add

    p = sub.add_parser(
        "add",
        help="Add library",
    )

    p.add_argument(
        "name",
    )

    p.set_defaults(
        func=cmd_add,
    )

    # remove

    p = sub.add_parser(
        "remove",
        help="Remove library",
    )

    p.add_argument(
        "name",
    )

    p.add_argument(
        "--delete",
        action="store_true",
        help="Delete directories",
    )

    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Show references",
    )

    p.set_defaults(
        func=cmd_remove,
    )

    # rename

    p = sub.add_parser(
        "rename",
        help="Rename library",
    )

    p.add_argument(
        "old",
    )

    p.add_argument(
        "new",
    )

    p.set_defaults(
        func=cmd_rename,
    )

    # list

    p = sub.add_parser(
        "list",
        help="List libraries",
    )

    p.set_defaults(
        func=cmd_list,
    )

    # doctor

    p = sub.add_parser(
        "doctor",
        help="Health check",
    )

    p.set_defaults(
        func=cmd_doctor,
    )

    return parser


# ─────────────────────────────────────────────────────────────

def main() -> None:

    parser = build_parser()

    args = parser.parse_args()

    args.func(args)


if __name__ == "__main__":

    main()
