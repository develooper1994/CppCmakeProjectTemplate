#!/usr/bin/env python3
"""install_deps.py — Simple dependency checker/suggester.

This script performs a minimal check for common required binaries and
prints guidance. It intentionally does not auto-install packages to
avoid surprising side-effects; it prints the platform-specific commands
to run instead.

Usage:
  python3 scripts/install_deps.py [--install] [--all]

Note: the `scripts/plugins/setup.py` plugin delegates to this module.
"""
from __future__ import annotations

import argparse
import shutil
import sys

MANDATORY = {
    "cmake": "cmake",
    "ninja": "ninja-build",
    "git": "git",
    "python3": "python3",
}

OPTIONAL = {
    "lcov": "lcov",
    "doxygen": "doxygen",
    "clang": "clang",
}


def find_missing(names: dict) -> dict:
    missing = {}
    for bin_name, pkg in names.items():
        if shutil.which(bin_name) is None:
            missing[bin_name] = pkg
    return missing


def suggest_install_cmd(missing: dict) -> str:
    # Only produce an apt-based suggestion; users on other distros should
    # adapt accordingly.
    if not missing:
        return ""
    pkgs = " ".join(sorted(set(missing.values())))
    return f"sudo apt install -y {pkgs}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="install_deps")
    parser.add_argument("--install", action="store_true", help="(informational) show installation command")
    parser.add_argument("--all", action="store_true", help="Include optional packages in the check")
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    missing = find_missing(MANDATORY)
    if args.all:
        missing.update(find_missing(OPTIONAL))

    if not missing:
        print("All required dependencies appear to be installed.")
        return 0

    print("Missing dependencies detected:")
    for k, v in missing.items():
        print(f" - {k}  (package: {v})")

    cmd = suggest_install_cmd(missing)
    if args.install:
        if cmd:
            print("\nSuggested command to install on Debian/Ubuntu:")
            print(cmd)
        else:
            print("No simple installation command available for your selection.")
    else:
        print("\nRun with --install to show install command, or install manually.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
