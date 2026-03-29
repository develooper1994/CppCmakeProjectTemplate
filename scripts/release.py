#!/usr/bin/env python3
"""Release helper for the repository.

Provides a simple CLI to bump/set the repository version and synchronize
the common version holders across the repository (CMakeLists, pyproject,
extension package.json, etc.). The canonical source of truth is the
`VERSION` file at the repository root; this script updates that file and
then applies sane replacements to other files.

Usage examples:
  python3 scripts/release.py bump minor --dry-run
  python3 scripts/release.py set 1.2.0+0
  python3 scripts/release.py set-revision 42
  python3 scripts/release.py tag --push

This script uses `Transaction` to apply changes atomically and will
commit the changes (and optionally tag) using `git`.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Optional

import sys
from pathlib import Path as _Path

# Ensure `scripts/` is on sys.path so we can import `core.*` packages.
SCRIPTS_DIR = _Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from core.utils.fileops import Transaction
from core.utils.version import read_version_file, write_version_file, Version, guess_revision_from_git
from core.utils.common import PROJECT_ROOT, Logger


VERSION_PATH = PROJECT_ROOT / "VERSION"


def update_files(v: Version, dry_run: bool = False) -> None:
    base = v.base()

    changes = []

    # 1) Update top-level CMakeLists.txt (project VERSION)
    cmake = PROJECT_ROOT / "CMakeLists.txt"
    if cmake.exists():
        txt = cmake.read_text(encoding="utf-8")
        new_txt, n = re.subn(r'(project\([^\n]*VERSION\s+)([0-9.]+)', lambda m: m.group(1) + base, txt, flags=re.IGNORECASE)
        if n:
            changes.append((cmake, new_txt))

    # 2) Update pyproject.toml version = "..."
    pyproj = PROJECT_ROOT / "pyproject.toml"
    if pyproj.exists():
        txt = pyproj.read_text(encoding="utf-8")
        new_txt, n = re.subn(r'(version\s*=\s*")([^"]+)(")', lambda m: m.group(1) + base + m.group(3), txt)
        if n:
            changes.append((pyproj, new_txt))

    # 3) Update extension/package.json
    ext_pkg = PROJECT_ROOT / "extension" / "package.json"
    if ext_pkg.exists():
        data = json.loads(ext_pkg.read_text(encoding="utf-8"))
        if data.get("version") != base:
            data["version"] = base
            changes.append((ext_pkg, json.dumps(data, indent=2) + "\n"))

    # 4) Update extension/package-lock.json (best-effort)
    ext_lock = PROJECT_ROOT / "extension" / "package-lock.json"
    if ext_lock.exists():
        try:
            data = json.loads(ext_lock.read_text(encoding="utf-8"))
            if data.get("version") != base:
                data["version"] = base
                changes.append((ext_lock, json.dumps(data, indent=2) + "\n"))
        except Exception:
            Logger.warn("Failed to parse extension/package-lock.json; skipping")

    # 5) Update extension UI default version strings (best-effort regex)
    ext_js = PROJECT_ROOT / "extension" / "src" / "extension.js"
    if ext_js.exists():
        txt = ext_js.read_text(encoding="utf-8")
        # replace value: '1.0.5' or value: '1.0.0' occurrences in showInputBox default
        new_txt, n = re.subn(r"(value:\s*')([0-9.]+(?:\.[0-9.]+)*(?:\+\d+)?)(')", lambda m: m.group(1) + str(v) + m.group(3), txt)
        if n:
            changes.append((ext_js, new_txt))

    if not changes:
        Logger.info("No file updates necessary (other files already in sync).")
        return

    if dry_run:
        Logger.info("Dry-run: the following changes would be applied:")
        for p, txt in changes:
            print(f"- {p}")
        return

    # Apply changes transactionally
    with Transaction(PROJECT_ROOT) as txn:
        # write VERSION first
        write_version_file(VERSION_PATH, v)

        for p, txt in changes:
            txn.safe_write_text(p, txt)

        # commit changes
        try:
            subprocess.run(["git", "add", str(VERSION_PATH)], check=True, cwd=PROJECT_ROOT)
            for p, _ in changes:
                subprocess.run(["git", "add", str(p)], check=True, cwd=PROJECT_ROOT)
            subprocess.run(["git", "commit", "-m", f"Bump version to {v}"], check=True, cwd=PROJECT_ROOT)
        except subprocess.CalledProcessError as e:
            Logger.error(f"Git commit failed: {e}")
            raise


def create_tag(v: Version, push: bool = False) -> None:
    tag_name = f"v{v.base()}"  # tag only with base version, omit +revision
    try:
        subprocess.run(["git", "tag", "-a", tag_name, "-m", f"Release {v}"], check=True, cwd=PROJECT_ROOT)
        Logger.success(f"Created tag {tag_name}")
        if push:
            subprocess.run(["git", "push", "origin", tag_name], check=True, cwd=PROJECT_ROOT)
            Logger.success(f"Pushed tag {tag_name} to origin")
    except subprocess.CalledProcessError as e:
        Logger.error(f"Git tag/push failed: {e}")
        raise


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="scripts/release.py")
    sub = p.add_subparsers(dest="cmd", required=True)

    pb = sub.add_parser("bump", help="Bump a part of the version")
    pb.add_argument("part", choices=["major", "middle", "minor"], help="Which part to bump")
    pb.add_argument("--dry-run", action="store_true")

    ps = sub.add_parser("set", help="Set exact version string (e.g. 1.2.3+45)")
    ps.add_argument("version")
    ps.add_argument("--dry-run", action="store_true")

    pr = sub.add_parser("set-revision", help="Set only the revision/build metadata")
    pr.add_argument("revision", type=int)
    pr.add_argument("--dry-run", action="store_true")

    pt = sub.add_parser("tag", help="Create git tag for current base version")
    pt.add_argument("--push", action="store_true", help="Push tag to origin")

    args = p.parse_args(argv)

    current = read_version_file(VERSION_PATH)

    if args.cmd == "bump":
        if args.part == "major":
            new = current.bump_major()
        elif args.part == "middle":
            new = current.bump_middle()
        else:
            new = current.bump_minor()
        # default revision: keep existing if non-null, otherwise guess from git
        if new.revision is None:
            new = new.set_revision(guess_revision_from_git())
        update_files(new, dry_run=bool(args.dry_run))
        return 0

    if args.cmd == "set":
        new = Version.parse(args.version)
        update_files(new, dry_run=bool(args.dry_run))
        return 0

    if args.cmd == "set-revision":
        new = current.set_revision(args.revision)
        update_files(new, dry_run=bool(args.dry_run))
        return 0

    if args.cmd == "tag":
        create_tag(current, push=bool(args.push))
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
