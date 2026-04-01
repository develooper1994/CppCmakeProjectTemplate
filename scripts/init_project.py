#!/usr/bin/env python3
"""
init_project.py — Rename the CppCmakeProjectTemplate to a custom name.

Usage:
    python3 scripts/init_project.py --name MyProject [--old-name CppCmakeProjectTemplate]

Replaces occurrences of the old project name in key files.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Files that typically contain the project name
TARGET_FILES = [
    "CMakeLists.txt",
    "README.md",
    "pyproject.toml",
    "tool.toml",
    "vcpkg.json",
    "conanfile.py",
    "docker/Dockerfile",
    "VERSION",
    "extension/package.json",
    ".github/workflows/*.yml",
]


def _collect_files(patterns: list[str]) -> list[Path]:
    files: list[Path] = []
    for pat in patterns:
        if "*" in pat:
            files.extend(PROJECT_ROOT.glob(pat))
        else:
            p = PROJECT_ROOT / pat
            if p.is_file():
                files.append(p)
    return files


def rename_project(new_name: str, old_name: str = "CppCmakeProjectTemplate",
                   dry_run: bool = False) -> None:
    files = _collect_files(TARGET_FILES)
    changed = 0
    for f in files:
        try:
            content = f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        new_content = content.replace(old_name, new_name)
        # Also handle lowercase/snake_case variant
        old_lower = re.sub(r"(?<=[a-z])(?=[A-Z])", "_", old_name).lower()
        new_lower = re.sub(r"(?<=[a-z])(?=[A-Z])", "_", new_name).lower()
        new_content = new_content.replace(old_lower, new_lower)

        if new_content != content:
            if dry_run:
                print(f"[dry-run] Would update {f.relative_to(PROJECT_ROOT)}")
            else:
                f.write_text(new_content, encoding="utf-8")
                print(f"✅ Updated {f.relative_to(PROJECT_ROOT)}")
            changed += 1

    if changed == 0:
        print("No files needed updating.")
    else:
        action = "would update" if dry_run else "updated"
        print(f"\n{changed} file(s) {action}.")


def main() -> None:
    p = argparse.ArgumentParser(
        prog="init_project",
        description="Rename the project after cloning",
    )
    p.add_argument("--name", required=True, help="New project name")
    p.add_argument("--old-name", default="CppCmakeProjectTemplate",
                   help="Current project name to replace (default: CppCmakeProjectTemplate)")
    p.add_argument("--dry-run", action="store_true",
                   help="Show what would change without modifying files")
    args = p.parse_args()
    rename_project(args.name, old_name=args.old_name, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
