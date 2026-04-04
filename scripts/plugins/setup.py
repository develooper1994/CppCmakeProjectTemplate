#!/usr/bin/env python3
"""
plugins/setup.py — Dependency checker/installer plugin.

Usage: tool setup [--install] [--do-install] [--all] [--env [DIR]] [--install-env] [--recreate]

  --install      Show the install command (informational)
  --do-install   Actually run 'sudo apt install ...' / 'brew install ...' to install
  --all          Include optional packages in the check/install
  --env [DIR]    Create/activate a Python venv (default dir: .venv)
  --install-env  Install requirements-dev.txt into the venv
  --recreate     Recreate venv if it already exists
"""
from __future__ import annotations

import argparse
import platform
import shlex
import subprocess
import sys
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
    "cmake":   "cmake",
    "ninja":   "ninja-build",
    "git":     "git",
    "python3": "python3",
}

OPTIONAL_SYS = {
    "lcov":        "lcov",
    "doxygen":     "doxygen",
    "clang":       "clang",
    "clang-tidy":  "clang-tidy",
    "cppcheck":    "cppcheck",
    "osv-scanner": "osv-scanner",
    "valgrind":    "valgrind",
    "ccache":      "ccache",
    "gitleaks":    "gitleaks",
}

# Map from package name to Homebrew formula (macOS)
_BREW_MAP: dict[str, str] = {
    "cmake":       "cmake",
    "ninja-build": "ninja",
    "git":         "git",
    "python3":     "python",
}

# Map from package name to winget ID (Windows)
_WINGET_MAP: dict[str, str] = {
    "cmake":       "Kitware.CMake",
    "ninja-build": "Ninja-build.Ninja",
    "git":         "Git.Git",
    "python3":     "Python.Python.3.12",
    "lcov":        "lcov",
    "doxygen":     "DimitriVanHeesch.Doxygen",
    "clang":       "LLVM.LLVM",
    "clang-tidy":  "LLVM.LLVM",
    "cppcheck":    "Cppcheck.Cppcheck",
    "ccache":      "ccache.ccache",
    "gitleaks":    "Gitleaks.Gitleaks",
}

# Map from package name to Chocolatey package (Windows)
_CHOCO_MAP: dict[str, str] = {
    "cmake":       "cmake",
    "ninja-build": "ninja",
    "git":         "git",
    "python3":     "python",
    "doxygen":     "doxygen.install",
    "clang":       "llvm",
    "clang-tidy":  "llvm",
    "cppcheck":    "cppcheck",
    "ccache":      "ccache",
}

# Map from package name to winget package ID (Windows)
_WINGET_MAP: dict[str, str] = {
    "cmake":       "Kitware.CMake",
    "ninja-build": "Ninja-build.Ninja",
    "git":         "Git.Git",
    "python3":     "Python.Python.3.12",
    "doxygen":     "DimitriVanHeesch.Doxygen",
    "clang":       "LLVM.LLVM",
    "clang-tidy":  "LLVM.LLVM",
    "ccache":      "ccache.ccache",
    "cppcheck":    "Cppcheck.Cppcheck",
}

# Map from package name to Chocolatey package (Windows)
_CHOCO_MAP: dict[str, str] = {
    "cmake":       "cmake",
    "ninja-build": "ninja",
    "git":         "git",
    "python3":     "python",
    "doxygen":     "doxygen.install",
    "clang":       "llvm",
    "clang-tidy":  "llvm",
    "ccache":      "ccache",
    "cppcheck":    "cppcheck",
}


def _detect_package_manager() -> str:
    """Return 'apt', 'brew', 'dnf', 'pacman', 'winget', 'choco', or 'unknown'."""
    sys_name = platform.system().lower()
    if sys_name == "darwin":
        if shutil.which("brew"):
            return "brew"
    if sys_name == "windows":
        if shutil.which("winget"):
            return "winget"
        if shutil.which("choco"):
            return "choco"
    for pm in ("apt-get", "dnf", "pacman"):
        if shutil.which(pm):
            return pm.split("-")[0]  # 'apt-get' -> 'apt'
    return "unknown"


def _build_install_cmd(pkg_manager: str, packages: list[str]) -> list[str] | None:
    """Return a ready-to-run install command list, or None if unsupported."""
    if pkg_manager == "apt":
        return ["sudo", "apt-get", "install", "-y"] + packages
    if pkg_manager == "brew":
        brew_pkgs = [_BREW_MAP.get(p, p) for p in packages]
        return ["brew", "install"] + list(dict.fromkeys(brew_pkgs))  # deduplicate
    if pkg_manager == "dnf":
        return ["sudo", "dnf", "install", "-y"] + packages
    if pkg_manager == "pacman":
        return ["sudo", "pacman", "-S", "--noconfirm"] + packages
    if pkg_manager == "winget":
        winget_pkgs = [_WINGET_MAP.get(p, p) for p in packages if p in _WINGET_MAP]
        if not winget_pkgs:
            return None
        return ["winget", "install", "--accept-source-agreements", "--accept-package-agreements"] + winget_pkgs
    if pkg_manager == "choco":
        choco_pkgs = [_CHOCO_MAP.get(p, p) for p in packages if p in _CHOCO_MAP]
        if not choco_pkgs:
            return None
        return ["choco", "install", "-y"] + list(dict.fromkeys(choco_pkgs))
    return None


import shutil  # noqa: E402 (after function def to avoid issue)


def main(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(prog="tool setup",
                                     description="Check and install project dependencies.")
    parser.add_argument("--install", action="store_true",
                        help="Show installation command (informational)")
    parser.add_argument("--do-install", action="store_true", dest="do_install",
                        help="Actually run the package manager to install missing packages")
    parser.add_argument("--all", action="store_true",
                        help="Include optional packages in the check/install")
    parser.add_argument("--env", nargs="?", const=".venv", default=None,
                        help="Create Python venv (optional dir, default: .venv)")
    parser.add_argument("--install-env", action="store_true", dest="install_env",
                        help="Install requirements-dev.txt into the created venv")
    parser.add_argument("--recreate", action="store_true",
                        help="Recreate venv if it already exists")
    args = parser.parse_args(argv)

    # ── 1. System Dependencies ──────────────────────────────────────────────
    deps_to_check = dict(MANDATORY_SYS)
    if args.all:
        deps_to_check.update(OPTIONAL_SYS)

    missing = find_missing_binaries(deps_to_check)

    if not missing:
        Logger.success("All system dependencies are installed.")
    else:
        Logger.warn("Missing system dependencies:")
        for bin_name, pkg in missing.items():
            print(f"  - {bin_name:<18} (package: {pkg})")

        pm = _detect_package_manager()
        pkg_list = sorted(set(missing.values()))
        install_cmd = _build_install_cmd(pm, pkg_list)

        if install_cmd is None:
            Logger.warn(f"Unsupported package manager '{pm}'. Install manually:")
            for p in pkg_list:
                print(f"  {p}")
        elif args.do_install:
            Logger.info(f"Running: {shlex.join(install_cmd)}")
            rc = subprocess.run(install_cmd).returncode
            if rc == 0:
                Logger.success("System packages installed successfully.")
            else:
                Logger.error(f"Install failed with exit code {rc}.")
                sys.exit(rc)
        elif args.install:
            print(f"\nInstall command ({pm}):\n  {shlex.join(install_cmd)}")
        else:
            print(f"\nRe-run with --install to see the install command, or --do-install to run it.")

    # ── 2. Python Venv ──────────────────────────────────────────────────────
    if args.env is not None:
        env_path = PROJECT_ROOT / args.env
        py_exe = create_venv(env_path, recreate=args.recreate)
        if args.install_env:
            install_python_requirements(py_exe, PROJECT_ROOT / "requirements-dev.txt")
        print_venv_activation(env_path)
