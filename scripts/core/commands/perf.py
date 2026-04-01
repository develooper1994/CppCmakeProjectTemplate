#!/usr/bin/env python3
"""
core/commands/perf.py — Performance analysis: build time, code size, benchmarks.
"""
from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path
from core.utils.common import (
    Logger,
    GlobalConfig,
    CLIResult,
    run_proc,
    run_capture,
    PROJECT_ROOT,
)

BUILD_DIR = PROJECT_ROOT / "build"
LOGS_DIR = PROJECT_ROOT / "build_logs"


def _find_active_build_dir() -> Path:
    """Find the most recently modified preset build directory under build/."""
    candidates = []
    for d in BUILD_DIR.iterdir():
        if d.is_dir() and (d / "CMakeCache.txt").exists():
            candidates.append(d)
    if candidates:
        # Pick most recently modified
        candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        Logger.info(f"Auto-detected build dir: {candidates[0]}")
        return candidates[0]
    return BUILD_DIR


def _find_binaries(build_dir: Path) -> list[Path]:
    """Find ELF/Mach-O binaries and static libraries in the build tree."""
    binaries = []
    skip_dirs = {"CMakeFiles", "_deps", "generated", "cmake_install.cmake"}

    # Search known artifact directories: bin/, lib/, apps/, libs/, tests/
    for subdir in ("bin", "lib", "apps", "libs", "tests"):
        search_root = build_dir / subdir
        if not search_root.exists():
            continue
        for f in search_root.rglob("*"):
            if not f.is_file():
                continue
            # Skip CMake internals
            if any(part in skip_dirs for part in f.parts):
                continue
            # Accept .a/.so/.dylib or executable ELF
            if f.suffix in (".a", ".so", ".dylib", ".dll", ".lib", ".exe"):
                binaries.append(f)
            elif f.suffix == "" and not f.name.startswith("."):
                # Check if it's an ELF binary (first bytes)
                try:
                    with open(f, "rb") as fh:
                        magic = fh.read(4)
                    if magic == b"\x7fELF" or magic[:2] == b"MZ":
                        binaries.append(f)
                except (OSError, PermissionError):
                    pass
    return sorted(binaries)


def _cmd_size(args) -> CLIResult:
    """Analyze binary sizes of built artifacts."""
    bd_arg = getattr(args, 'build_dir', None)
    build_dir = Path(bd_arg) if bd_arg else _find_active_build_dir()

    binaries = _find_binaries(build_dir)

    if not binaries:
        return CLIResult(success=False, code=1, message=f"No binaries found in {build_dir}/bin or {build_dir}/lib")

    size_tool = shutil.which("size")
    bloaty_tool = shutil.which("bloaty")

    results = []
    for b in binaries:
        stat = b.stat()
        entry = {
            "file": str(b.relative_to(PROJECT_ROOT)),
            "size_bytes": stat.st_size,
            "size_human": _human_size(stat.st_size),
        }

        # Use `size` for section breakdown
        if size_tool:
            try:
                out, rc = run_capture([size_tool, "--format=berkeley", str(b)])
                if rc == 0:
                    entry["sections"] = out.strip()
            except Exception:
                pass

        results.append(entry)

    # Display
    Logger.info(f"{'File':<50} {'Size':>12}")
    Logger.info("-" * 64)
    for r in results:
        Logger.info(f"{r['file']:<50} {r['size_human']:>12}")

    # Save report
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = LOGS_DIR / "size_report.json"
    report_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    Logger.info(f"\nDetailed report: {report_path}")

    if bloaty_tool and binaries:
        Logger.info("\nBloaty deep analysis (first binary):")
        run_proc([bloaty_tool, str(binaries[0])], check=False)

    return CLIResult(success=True, message=f"Analyzed {len(results)} artifacts", data=results)


def _cmd_build_time(args) -> CLIResult:
    """Analyze build times using CMake/Ninja timing or a timed rebuild."""
    bd_arg = getattr(args, 'build_dir', None)
    build_dir = Path(bd_arg) if bd_arg else _find_active_build_dir()
    preset = getattr(args, 'preset', None)

    # Check for Ninja .ninja_log
    ninja_log = build_dir / ".ninja_log"
    if ninja_log.exists():
        return _analyze_ninja_log(ninja_log)

    # Check for CMake time trace (.json files from -ftime-trace)
    time_traces = list(build_dir.rglob("*.json"))
    time_traces = [t for t in time_traces if "time-trace" in t.name.lower()]

    # Fall back to timed rebuild
    Logger.info("No Ninja log found. Running timed build...")
    start = time.monotonic()
    cmd = ["cmake", "--build", str(build_dir)]
    if preset:
        cmd = ["cmake", "--build", "--preset", preset]
    rc = run_proc(cmd, check=False)
    elapsed = time.monotonic() - start

    result = {
        "total_seconds": round(elapsed, 2),
        "total_human": f"{elapsed:.2f}s",
        "exit_code": rc,
    }

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    report = LOGS_DIR / "build_time_report.json"
    report.write_text(json.dumps(result, indent=2), encoding="utf-8")

    Logger.info(f"Build completed in {elapsed:.2f}s (exit code {rc})")
    Logger.info(f"Report: {report}")

    return CLIResult(success=(rc == 0), message=f"Build time: {elapsed:.2f}s", data=result)


def _analyze_ninja_log(ninja_log: Path) -> CLIResult:
    """Parse .ninja_log for per-target build times."""
    Logger.info(f"Analyzing Ninja build log: {ninja_log}")
    entries = []
    try:
        for line in ninja_log.read_text(encoding="utf-8").splitlines():
            if line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) >= 4:
                start_ms = int(parts[0])
                end_ms = int(parts[1])
                target = parts[3] if len(parts) > 3 else parts[2]
                duration_s = (end_ms - start_ms) / 1000.0
                entries.append({"target": target, "duration_s": round(duration_s, 3)})
    except Exception as e:
        return CLIResult(success=False, code=1, message=f"Failed to parse ninja log: {e}")

    # Sort by duration descending
    entries.sort(key=lambda x: x["duration_s"], reverse=True)

    # Show top 20
    Logger.info(f"\n{'Target':<70} {'Time':>10}")
    Logger.info("-" * 82)
    for e in entries[:20]:
        Logger.info(f"{e['target']:<70} {e['duration_s']:>8.3f}s")

    total = sum(e["duration_s"] for e in entries)
    Logger.info(f"\nTotal compilation time: {total:.2f}s across {len(entries)} targets")

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    report = LOGS_DIR / "build_time_report.json"
    report.write_text(json.dumps({"total_seconds": round(total, 2), "targets": entries}, indent=2), encoding="utf-8")
    Logger.info(f"Report: {report}")

    return CLIResult(success=True, message=f"Build time analysis: {total:.2f}s total", data=entries)


def _human_size(size_bytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if abs(size_bytes) < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def perf_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tool perf", description="Performance analysis tools")
    sub = parser.add_subparsers(dest="subcommand")

    p = sub.add_parser("size", help="Analyze binary sizes of built artifacts")
    p.add_argument("--build-dir", default=None, help="Build directory (default: build/)")
    p.set_defaults(func=_cmd_size)

    p = sub.add_parser("build-time", help="Analyze build times")
    p.add_argument("--build-dir", default=None, help="Build directory (default: build/)")
    p.add_argument("--preset", default=None, help="CMake preset for timed rebuild")
    p.set_defaults(func=_cmd_build_time)

    return parser


def main(argv: list[str]) -> None:
    parser = perf_parser()
    args = parser.parse_args(argv if argv else [])
    if hasattr(args, "func"):
        args.func(args).exit()
    else:
        parser.print_help()
