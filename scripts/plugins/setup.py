#!/usr/bin/env python3
"""
plugins/setup.py — Dependency checker/installer plugin.

Usage: tool setup [--install] [--all] [--env [DIR]] [--install-env] [--recreate]
"""
from __future__ import annotations

import argparse
from pathlib import Path
from core.utils.common import (
    Logger,
    PROJECT_ROOT,
    find_missing_binaries,
    create_venv,
    install_python_requirements,
    print_venv_activation,
)

PLUGIN_META = {
    "name": "setup",
    "description": "Check and optionally install system and Python dependencies for the project.",
}

MANDATORY_SYS = {
    "cmake": "cmake",
    "ninja": "ninja-build",
    "git": "git",
    "python3": "python3",
}

OPTIONAL_SYS = {
    "lcov": "lcov",
    "doxygen": "doxygen",
    "clang": "clang",
    "cppcheck": "cppcheck",
}


def main(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(prog="tool setup")
    parser.add_argument("--install", action="store_true", help="(informational) show installation command")
    parser.add_argument("--all", action="store_true", help="Include optional packages in the check")
    parser.add_argument("--env", nargs="?", const=".venv", default=None, help="Create Python venv (optional dir, default: .venv)")
    parser.add_argument("--install-env", action="store_true", help="Install requirements-dev.txt into created venv")
    parser.add_argument("--recreate", action="store_true", help="Recreate venv if it exists")
    args = parser.parse_args(argv)

    # 1. System Dependencies
    missing = find_missing_binaries(MANDATORY_SYS)
    if args.all:
        missing.update(find_missing_binaries(OPTIONAL_SYS))

    if not missing:
        Logger.success("All system dependencies appear to be installed.")
    else:
        Logger.warn("Missing system dependencies detected:")
        for k, v in missing.items():
            print(f" - {k}  (package: {v})")
        
        pkgs = " ".join(sorted(set(missing.values())))
        cmd = f"sudo apt install -y {pkgs}"
        if args.install:
            print(f"\nSuggested command to install on Debian/Ubuntu:\n{cmd}")
        else:
            print("\nRun with --install to show install command.")

    # 2. Python Venv
    if args.env is not None:
        env_path = PROJECT_ROOT / args.env
        py_exe = create_venv(env_path, recreate=args.recreate)
        if args.install_env:
            install_python_requirements(py_exe, PROJECT_ROOT / "requirements-dev.txt")
        print_venv_activation(env_path)
