"""Shared helpers and constants for the perf subcommands."""
from __future__ import annotations

import shutil
from pathlib import Path

from core.utils.common import Logger, PROJECT_ROOT

BUILD_DIR = PROJECT_ROOT / "build"
LOGS_DIR = PROJECT_ROOT / "build_logs"
BASELINE_FILE = LOGS_DIR / "perf_baseline.json"
BENCH_RESULTS_FILE = LOGS_DIR / "bench_results.json"


def _find_active_build_dir() -> Path:
    """Find the most recently modified preset build directory under build/."""
    candidates = []
    for d in BUILD_DIR.iterdir():
        if d.is_dir() and (d / "CMakeCache.txt").exists():
            candidates.append(d)
    if candidates:
        candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        Logger.info(f"Auto-detected build dir: {candidates[0]}")
        return candidates[0]
    return BUILD_DIR


def _find_binaries(build_dir: Path) -> list[Path]:
    """Find ELF/Mach-O binaries and static libraries in the build tree."""
    binaries = []
    skip_dirs = {"CMakeFiles", "_deps", "generated", "cmake_install.cmake"}

    for subdir in ("bin", "lib", "apps", "libs", "tests"):
        search_root = build_dir / subdir
        if not search_root.exists():
            continue
        for f in search_root.rglob("*"):
            if not f.is_file():
                continue
            if any(part in skip_dirs for part in f.parts):
                continue
            if f.suffix in (".a", ".so", ".dylib", ".dll", ".lib", ".exe"):
                binaries.append(f)
            elif f.suffix == "" and not f.name.startswith("."):
                try:
                    with open(f, "rb") as fh:
                        magic = fh.read(4)
                    if magic == b"\x7fELF" or magic[:2] == b"MZ":
                        binaries.append(f)
                except (OSError, PermissionError):
                    pass
    return sorted(binaries)


def _human_size(size_bytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if abs(size_bytes) < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def _parse_ninja_log(ninja_log: Path) -> list[dict]:
    """Parse .ninja_log → list of {target, duration_s}."""
    entries = []
    for line in ninja_log.read_text(encoding="utf-8").splitlines():
        if line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) >= 4:
            start_ms = int(parts[0])
            end_ms = int(parts[1])
            target = parts[3] if len(parts) > 3 else parts[2]
            entries.append({"target": target, "duration_s": round((end_ms - start_ms) / 1000.0, 3)})
    return entries


def _detect_available_tools() -> dict:
    """Probe for optional analysis tools. Returns {name: path|None}."""
    tools = [
        "nm", "size", "objdump", "bloaty", "perf", "valgrind",
        "hyperfine", "gprof", "uftrace", "stackcollapse-perf.pl", "flamegraph.pl",
        "bpftrace",
    ]
    return {t: shutil.which(t) for t in tools}


def _safe_relative(path: Path, base: Path) -> str:
    """Return relative path string, falling back to the absolute path."""
    try:
        return str(path.relative_to(base))
    except ValueError:
        return str(path)
