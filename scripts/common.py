#!/usr/bin/env python3
"""
common.py — Shared utilities for all scripts in scripts/.

Import:
    from common import PROJECT_ROOT, default_preset, run, header, get_project_version
"""

from __future__ import annotations

import json
import platform
import re
import subprocess
import sys
from pathlib import Path

# ──────────────────────────────────────────────────────────────────────────────
# Project root
# ──────────────────────────────────────────────────────────────────────────────

def find_project_root(start: Path) -> Path:
    p = start.resolve()
    if p.is_file():
        p = p.parent
    while True:
        if (
            (p / "libs").is_dir()
            and (p / "tests").is_dir()
            and (p / "apps").is_dir()
            and (p / "scripts").is_dir()
        ):
            return p
        if p.parent == p:
            raise RuntimeError(
                "Project root not found. Expected libs/, tests/, apps/, scripts/."
            )
        p = p.parent


PROJECT_ROOT: Path = find_project_root(Path(__file__).resolve())

# ──────────────────────────────────────────────────────────────────────────────
# Presets
# ──────────────────────────────────────────────────────────────────────────────

DEFAULT_PRESET: dict[str, str] = {
    "Linux":   "gcc-debug-static-x86_64",
    "Windows": "msvc-debug-static-x64",
    "Darwin":  "clang-debug-static-x86_64",
}


def default_preset() -> str:
    return DEFAULT_PRESET.get(platform.system(), "gcc-debug-static-x86_64")


def list_presets(root: Path = PROJECT_ROOT) -> list[str]:
    """Return all non-hidden configurePreset names from CMakePresets.json."""
    presets_file = root / "CMakePresets.json"
    if not presets_file.exists():
        return []
    data = json.loads(presets_file.read_text(encoding="utf-8"))
    return [
        p["name"]
        for p in data.get("configurePresets", [])
        if not p.get("hidden", False)
    ]


# ──────────────────────────────────────────────────────────────────────────────
# Version
# ──────────────────────────────────────────────────────────────────────────────

def get_project_version(root: Path = PROJECT_ROOT) -> str:
    """Version resolution order:
    1. CMakeLists.txt project(... VERSION X.Y.Z ...)
    2. Git tag (git describe --tags --abbrev=0)
    3. Fallback '0.0.0'
    """
    cmake_path = root / "CMakeLists.txt"
    if cmake_path.exists():
        # Strip comments before parsing so commented-out VERSION lines are ignored
        clean = re.sub(r'#.*', '', cmake_path.read_text(encoding="utf-8"))
        m = re.search(r'project\s*\([^)]*VERSION\s+([\d.]+)', clean, re.IGNORECASE | re.DOTALL)
        if m:
            return m.group(1)
    # Git fallback
    try:
        tag = subprocess.check_output(
            ["git", "describe", "--tags", "--abbrev=0"],
            cwd=root, stderr=subprocess.DEVNULL,
        ).decode().strip()
        return re.sub(r'^v', '', tag)
    except Exception:
        pass
    return "0.0.0"


def get_project_name(root: Path = PROJECT_ROOT) -> str:
    """Read project name from root CMakeLists.txt."""
    cmake = (root / "CMakeLists.txt").read_text(encoding="utf-8")
    m = re.search(r'project\s*\(\s*(\S+)', cmake, re.IGNORECASE)
    return m.group(1) if m else "CppProject"


# ──────────────────────────────────────────────────────────────────────────────
# CMake target listing
# ──────────────────────────────────────────────────────────────────────────────

def list_lib_targets(root: Path = PROJECT_ROOT) -> list[str]:
    libs_dir = root / "libs"
    if not libs_dir.exists():
        return []
    return sorted(
        p.parent.name
        for p in libs_dir.rglob("CMakeLists.txt")
        if p.parent != libs_dir
    )


def list_app_targets(root: Path = PROJECT_ROOT) -> list[str]:
    apps_dir = root / "apps"
    if not apps_dir.exists():
        return []
    return sorted(
        p.parent.name
        for p in apps_dir.rglob("CMakeLists.txt")
        if p.parent != apps_dir
    )


def list_all_targets(root: Path = PROJECT_ROOT) -> dict[str, list[str]]:
    return {
        "libs": list_lib_targets(root),
        "apps": list_app_targets(root),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Process runner
# ──────────────────────────────────────────────────────────────────────────────

def run(
    cmd: list[str],
    *,
    cwd: Path = PROJECT_ROOT,
    log: Path | None = None,
    check: bool = True,
) -> int:
    """Run a command, optionally tee-ing stdout+stderr to a log file.
    Returns the exit code."""
    print(f"  --> {' '.join(str(c) for c in cmd)}")
    if log:
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("w", encoding="utf-8") as f:
            result = subprocess.run(
                cmd, cwd=cwd,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            )
            f.write(result.stdout)
            print(result.stdout, end="")
    else:
        result = subprocess.run(cmd, cwd=cwd)

    if check and result.returncode != 0:
        msg = f"❌ FAILED (exit {result.returncode})"
        if log:
            msg += f" — log: {log}"
        print(msg, file=sys.stderr)
        sys.exit(result.returncode)

    return result.returncode


# ──────────────────────────────────────────────────────────────────────────────
# Display
# ──────────────────────────────────────────────────────────────────────────────

def header(title: str, subtitle: str | None = None) -> None:
    print("=" * 52)
    print(f"  {title}")
    if subtitle:
        print(f"  {subtitle}")
    print(f"  Root: {PROJECT_ROOT}")
    print("=" * 52)


def fail(msg: str, code: int = 1) -> "NoReturn":
    print(f"❌  {msg}", file=sys.stderr)
    raise SystemExit(code)
