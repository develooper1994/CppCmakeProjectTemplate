#!/usr/bin/env python3
"""
install_deps.py — Install required and optional project dependencies.

Usage:
    python3 scripts/install_deps.py           # check only
    python3 scripts/install_deps.py --install # install missing mandatory deps
    python3 scripts/install_deps.py --all     # install mandatory + all optional
"""

from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

SYSTEM = platform.system()   # Linux | Windows | Darwin

# ──────────────────────────────────────────────────────────────────────────────
# Dependency definitions
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class Dep:
    name: str
    check_cmd: list[str]          # command + args whose exit 0 means "installed"
    apt: str  = ""                # apt package name (Ubuntu/Debian)
    brew: str = ""                # brew formula (macOS)
    note: str = ""                # human hint for unsupported platforms
    optional: bool = False
    category: str = "core"

DEPS: list[Dep] = [
    # ── Mandatory ───────────────────────────────────────────────────────────
    Dep("CMake 3.25+",   ["cmake", "--version"],
        apt="cmake", brew="cmake",
        note="https://cmake.org/download/"),
    Dep("Ninja",         ["ninja", "--version"],
        apt="ninja-build", brew="ninja"),
    Dep("GCC",           ["gcc", "--version"],
        apt="build-essential", brew="gcc",
        note="On Windows use MSVC or MinGW"),
    Dep("Python 3.8+",   ["python3", "--version"],
        apt="python3", brew="python@3"),
    Dep("Git",           ["git", "--version"],
        apt="git", brew="git"),

    # ── Optional — quality tools ─────────────────────────────────────────────
    Dep("Clang",         ["clang", "--version"],
        apt="clang", brew="llvm",
        optional=True, category="compiler"),
    Dep("clang-tidy",    ["clang-tidy", "--version"],
        apt="clang-tidy", brew="llvm",
        optional=True, category="quality"),
    Dep("cppcheck",      ["cppcheck", "--version"],
        apt="cppcheck", brew="cppcheck",
        optional=True, category="quality"),
    Dep("lcov",          ["lcov", "--version"],
        apt="lcov", brew="lcov",
        optional=True, category="quality"),
    Dep("Doxygen",       ["doxygen", "--version"],
        apt="doxygen", brew="doxygen",
        optional=True, category="docs"),
    Dep("Valgrind",      ["valgrind", "--version"],
        apt="valgrind",
        note="Linux only — not available on macOS/Windows",
        optional=True, category="quality"),

    # ── Optional — frameworks ────────────────────────────────────────────────
    Dep("Qt6",           ["qmake6", "--version"],
        apt="qt6-base-dev", brew="qt@6",
        note="Required only when ENABLE_QT=ON",
        optional=True, category="framework"),
    Dep("Boost",         ["dpkg", "-s", "libboost-dev"],
        apt="libboost-all-dev", brew="boost",
        note="Required only when ENABLE_BOOST=ON",
        optional=True, category="framework"),

    # ── Optional — deployment / extension ───────────────────────────────────
    Dep("rsync",         ["rsync", "--version"],
        apt="rsync", brew="rsync",
        optional=True, category="deploy"),
    Dep("Node.js",       ["node", "--version"],
        apt="nodejs", brew="node",
        note="Required to build the VS Code extension (.vsix)",
        optional=True, category="extension"),
    Dep("npm",           ["npm", "--version"],
        apt="npm", brew="node",
        optional=True, category="extension"),
    Dep("textual (pip)", ["python3", "-c", "import textual"],
        apt="",
        note="TUI: pip3 install textual --break-system-packages",
        optional=True, category="extension"),

    # ── Optional — cross-compile / embedded ─────────────────────────────────
    Dep("crossbuild-i386", ["dpkg", "-s", "crossbuild-essential-i386"],
        apt="crossbuild-essential-i386",
        note="Linux only — provides i686-linux-gnu-gcc/g++ for x86 presets",
        optional=True, category="embedded"),
    Dep("arm-none-eabi-gcc", ["arm-none-eabi-gcc", "--version"],
        apt="gcc-arm-none-eabi binutils-arm-none-eabi",
        note="Required for embedded-arm-none-eabi preset",
        optional=True, category="embedded"),
]

# ──────────────────────────────────────────────────────────────────────────────
# Check helpers
# ──────────────────────────────────────────────────────────────────────────────

def is_present(dep: Dep) -> bool:
    try:
        subprocess.run(dep.check_cmd, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def install_apt(packages: str) -> bool:
    print(f"  --> sudo apt-get install -y {packages}")
    r = subprocess.run(["sudo", "apt-get", "install", "-y", *packages.split()])
    return r.returncode == 0


def install_brew(formula: str) -> bool:
    print(f"  --> brew install {formula}")
    r = subprocess.run(["brew", "install", *formula.split()])
    return r.returncode == 0


def try_install(dep: Dep) -> bool:
    if SYSTEM == "Linux"  and dep.apt:
        return install_apt(dep.apt)
    if SYSTEM == "Darwin" and dep.brew:
        return install_brew(dep.brew)
    print(f"  ⚠  Cannot auto-install on {SYSTEM}.")
    if dep.note:
        print(f"     {dep.note}")
    return False


# ──────────────────────────────────────────────────────────────────────────────
# Main logic
# ──────────────────────────────────────────────────────────────────────────────

def run(install: bool, all_deps: bool) -> None:
    targets = [d for d in DEPS if all_deps or not d.optional]

    ok = missing_mandatory = missing_optional = 0

    print(f"\n{'='*52}")
    print(f"  Dependency check — {SYSTEM}")
    print(f"{'='*52}\n")

    for dep in targets:
        present = is_present(dep)
        tag     = "[mandatory]" if not dep.optional else f"[optional/{dep.category}]"
        status  = "✅" if present else ("⚠ " if dep.optional else "❌")
        print(f"  {status}  {dep.name:<28} {tag}")
        if dep.note and not present:
            print(f"         ↳ {dep.note}")

        if present:
            ok += 1
        elif not dep.optional:
            missing_mandatory += 1
            if install:
                print(f"     Installing {dep.name}...")
                if not try_install(dep):
                    print(f"  ❌ Failed to install {dep.name}", file=sys.stderr)
        else:
            missing_optional += 1

    print(f"\n  ✅ Present  : {ok}")
    if missing_mandatory:
        print(f"  ❌ Missing  (mandatory): {missing_mandatory}")
    if missing_optional:
        print(f"  ⚠  Missing  (optional) : {missing_optional}")

    if missing_mandatory and not install:
        print("\n  Run with --install to auto-install missing mandatory deps.")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Check/install project dependencies")
    parser.add_argument("--install", action="store_true",
                        help="Install missing mandatory dependencies")
    parser.add_argument("--all",     action="store_true",
                        help="Check and optionally install all deps (mandatory + optional)")
    args = parser.parse_args()
    run(install=args.install, all_deps=args.all)


if __name__ == "__main__":
    main()
