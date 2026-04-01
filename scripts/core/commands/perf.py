#!/usr/bin/env python3
"""
core/commands/perf.py — Performance analysis: build time, code size, benchmarks,
                         budget tracking, valgrind, and build-graph visualization.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys
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
    try:
        entries = _parse_ninja_log(ninja_log)
    except Exception as e:
        return CLIResult(success=False, code=1, message=f"Failed to parse ninja log: {e}")

    entries.sort(key=lambda x: x["duration_s"], reverse=True)

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


# ---------------------------------------------------------------------------
# Performance Budget & Tracking
# ---------------------------------------------------------------------------

BASELINE_FILE = LOGS_DIR / "perf_baseline.json"
BENCH_RESULTS_FILE = LOGS_DIR / "bench_results.json"


def _cmd_track(args) -> CLIResult:
    """Capture current size + build-time snapshot as baseline."""
    bd_arg = getattr(args, "build_dir", None)
    build_dir = Path(bd_arg) if bd_arg else _find_active_build_dir()

    # --- size snapshot ---
    binaries = _find_binaries(build_dir)
    size_data: list[dict] = []
    for b in binaries:
        size_data.append({"file": str(b.relative_to(PROJECT_ROOT)), "size_bytes": b.stat().st_size})

    # --- build-time snapshot (from ninja log if available) ---
    build_time: float | None = None
    ninja_log = build_dir / ".ninja_log"
    if ninja_log.exists():
        try:
            entries = _parse_ninja_log(ninja_log)
            build_time = round(sum(e["duration_s"] for e in entries), 2)
        except Exception:
            pass

    baseline = {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "build_dir": str(build_dir.relative_to(PROJECT_ROOT)),
        "sizes": size_data,
        "build_time_s": build_time,
    }

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    BASELINE_FILE.write_text(json.dumps(baseline, indent=2), encoding="utf-8")
    Logger.info(f"Baseline saved → {BASELINE_FILE}")
    Logger.info(f"  Artifacts tracked: {len(size_data)}")
    if build_time is not None:
        Logger.info(f"  Build time: {build_time:.2f}s")
    return CLIResult(success=True, message="Baseline captured", data=baseline)


def _cmd_check_budget(args) -> CLIResult:
    """Compare current build against baseline; fail if regressions exceed thresholds."""
    if not BASELINE_FILE.exists():
        return CLIResult(success=False, code=1, message=f"No baseline found. Run 'tool perf track' first.")

    baseline = json.loads(BASELINE_FILE.read_text(encoding="utf-8"))
    bd_arg = getattr(args, "build_dir", None)
    build_dir = Path(bd_arg) if bd_arg else _find_active_build_dir()

    size_threshold_pct: float = getattr(args, "size_threshold", None)
    if size_threshold_pct is None:
        from core.utils.common import GlobalConfig
        size_threshold_pct = GlobalConfig.PERF_SIZE_THRESHOLD_PCT
    time_threshold_pct: float = getattr(args, "time_threshold", None)
    if time_threshold_pct is None:
        from core.utils.common import GlobalConfig
        time_threshold_pct = GlobalConfig.PERF_TIME_THRESHOLD_PCT

    # --- compare sizes ---
    baseline_sizes = {e["file"]: e["size_bytes"] for e in baseline.get("sizes", [])}
    binaries = _find_binaries(build_dir)
    regressions: list[str] = []
    Logger.info(f"\n{'Artifact':<55} {'Baseline':>12} {'Current':>12} {'Δ%':>8}")
    Logger.info("-" * 92)

    for b in binaries:
        rel = str(b.relative_to(PROJECT_ROOT))
        current_bytes = b.stat().st_size
        if rel in baseline_sizes:
            base_bytes = baseline_sizes[rel]
            if base_bytes > 0:
                delta_pct = (current_bytes - base_bytes) / base_bytes * 100
            else:
                delta_pct = 0.0
            marker = " ⚠" if delta_pct > size_threshold_pct else ""
            Logger.info(
                f"{rel:<55} {_human_size(base_bytes):>12} {_human_size(current_bytes):>12} "
                f"{delta_pct:>+7.1f}%{marker}"
            )
            if delta_pct > size_threshold_pct:
                regressions.append(
                    f"SIZE: {rel} grew {delta_pct:.1f}% (threshold {size_threshold_pct:.0f}%)"
                )
        else:
            Logger.info(f"{rel:<55} {'(new)':>12} {_human_size(current_bytes):>12} {'N/A':>8}")

    # --- compare build time ---
    base_time = baseline.get("build_time_s")
    ninja_log = build_dir / ".ninja_log"
    if base_time and ninja_log.exists():
        try:
            entries = _parse_ninja_log(ninja_log)
            cur_time = sum(e["duration_s"] for e in entries)
            delta_pct = (cur_time - base_time) / base_time * 100 if base_time > 0 else 0.0
            marker = " ⚠" if delta_pct > time_threshold_pct else ""
            Logger.info(f"\nBuild time: baseline={base_time:.2f}s  current={cur_time:.2f}s  Δ={delta_pct:+.1f}%{marker}")
            if delta_pct > time_threshold_pct:
                regressions.append(
                    f"BUILDTIME: grew {delta_pct:.1f}% (threshold {time_threshold_pct:.0f}%)"
                )
        except Exception:
            pass

    if regressions:
        Logger.error(f"\n{len(regressions)} regression(s) detected:")
        for r in regressions:
            Logger.error(f"  • {r}")
        return CLIResult(success=False, code=1, message="Budget check failed", data={"regressions": regressions})

    Logger.info("\nAll budgets OK — no regressions detected.")
    return CLIResult(success=True, message="Budget check passed")


# ---------------------------------------------------------------------------
# Google Benchmark runner
# ---------------------------------------------------------------------------

def _cmd_bench(args) -> CLIResult:
    """Discover and run Google Benchmark binaries; save JSON results."""
    bd_arg = getattr(args, "build_dir", None)
    build_dir = Path(bd_arg) if bd_arg else _find_active_build_dir()
    filter_pattern: str | None = getattr(args, "filter", None)
    save_baseline: bool = getattr(args, "save_baseline", False)
    compare: bool = getattr(args, "compare", False)

    # Discover benchmark executables (named *bench* or *benchmark*)
    bench_bins: list[Path] = []
    for candidate in build_dir.rglob("*"):
        if not candidate.is_file():
            continue
        name = candidate.name.lower()
        if ("bench" in name or "benchmark" in name) and candidate.stat().st_mode & 0o111:
            try:
                with open(candidate, "rb") as fh:
                    if fh.read(4) == b"\x7fELF":
                        bench_bins.append(candidate)
            except OSError:
                pass

    if not bench_bins:
        return CLIResult(
            success=False, code=1,
            message="No benchmark binaries found. Build with ENABLE_BENCHMARKS=ON."
        )

    all_results: list[dict] = []
    for bb in bench_bins:
        Logger.info(f"\nRunning: {bb.name}")
        cmd = [str(bb), "--benchmark_format=json"]
        if filter_pattern:
            cmd.append(f"--benchmark_filter={filter_pattern}")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode == 0 and result.stdout.strip():
                data = json.loads(result.stdout)
                for bm in data.get("benchmarks", []):
                    bm["binary"] = bb.name
                    all_results.append(bm)
                    Logger.info(
                        f"  {bm.get('name','?'):<50} "
                        f"{bm.get('real_time', 0):>10.1f} ns/iter"
                    )
        except subprocess.TimeoutExpired:
            Logger.error(f"  Timeout running {bb.name}")
        except (OSError, json.JSONDecodeError) as e:
            Logger.error(f"  Error: {e}")

    if not all_results:
        return CLIResult(success=False, code=1, message="No benchmark results collected")

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    report = {"timestamp": datetime.datetime.utcnow().isoformat() + "Z", "benchmarks": all_results}
    BENCH_RESULTS_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
    Logger.info(f"\nResults saved → {BENCH_RESULTS_FILE}")

    if save_baseline:
        baseline_bench = LOGS_DIR / "bench_baseline.json"
        baseline_bench.write_text(json.dumps(report, indent=2), encoding="utf-8")
        Logger.info(f"Baseline saved → {baseline_bench}")

    if compare:
        baseline_bench = LOGS_DIR / "bench_baseline.json"
        if baseline_bench.exists():
            _compare_benchmarks(baseline_bench, all_results)
        else:
            Logger.warning("No bench baseline found. Run with --save-baseline first.")

    return CLIResult(success=True, message=f"Ran {len(all_results)} benchmarks", data=report)


def _compare_benchmarks(baseline_path: Path, current: list[dict]) -> None:
    """Print benchmark comparison table against baseline."""
    baseline_data = json.loads(baseline_path.read_text(encoding="utf-8"))
    baseline_map = {b["name"]: b.get("real_time", 0) for b in baseline_data.get("benchmarks", [])}

    Logger.info(f"\n{'Benchmark':<55} {'Baseline':>12} {'Current':>12} {'Δ%':>8}")
    Logger.info("-" * 92)
    for bm in current:
        name = bm.get("name", "?")
        cur_t = bm.get("real_time", 0)
        if name in baseline_map:
            base_t = baseline_map[name]
            delta = (cur_t - base_t) / base_t * 100 if base_t > 0 else 0.0
            marker = " ⚠" if delta > 10 else ""
            Logger.info(f"{name:<55} {base_t:>10.1f} ns {cur_t:>10.1f} ns {delta:>+7.1f}%{marker}")
        else:
            Logger.info(f"{name:<55} {'(new)':>12} {cur_t:>10.1f} ns {'N/A':>8}")


# ---------------------------------------------------------------------------
# Valgrind / memory analysis
# ---------------------------------------------------------------------------

def _cmd_valgrind(args) -> CLIResult:
    """Run a target binary under Valgrind memcheck or massif."""
    binary: str | None = getattr(args, "binary", None)
    tool_name: str = getattr(args, "vg_tool", "memcheck")
    extra_args: list[str] = getattr(args, "extra_args", []) or []

    if not binary:
        return CLIResult(success=False, code=1, message="Specify binary with --binary <path>")

    valgrind = shutil.which("valgrind")
    if not valgrind:
        return CLIResult(success=False, code=1, message="valgrind not found. Install: sudo apt install valgrind")

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    bin_path = Path(binary)
    if not bin_path.is_absolute():
        bin_path = PROJECT_ROOT / binary

    if tool_name == "massif":
        out_file = LOGS_DIR / "massif.out"
        cmd = [
            valgrind, f"--tool={tool_name}",
            f"--massif-out-file={out_file}",
            str(bin_path),
        ] + extra_args
        Logger.info(f"Running massif → {out_file}")
    else:
        xml_out = LOGS_DIR / "valgrind_memcheck.xml"
        cmd = [
            valgrind,
            f"--tool={tool_name}",
            "--leak-check=full",
            "--show-leak-kinds=all",
            "--track-origins=yes",
            "--error-exitcode=1",
            f"--xml=yes",
            f"--xml-file={xml_out}",
            str(bin_path),
        ] + extra_args
        Logger.info(f"Running memcheck → {xml_out}")

    rc = run_proc(cmd, check=False)

    if tool_name == "massif":
        ms_print = shutil.which("ms_print")
        if ms_print and out_file.exists():
            summary_path = LOGS_DIR / "massif_summary.txt"
            result = subprocess.run([ms_print, str(out_file)], capture_output=True, text=True)
            summary_path.write_text(result.stdout, encoding="utf-8")
            Logger.info(f"Massif summary → {summary_path}")
            # Print peak
            for line in result.stdout.splitlines()[:30]:
                Logger.info(line)

    return CLIResult(
        success=(rc == 0),
        code=rc,
        message=f"valgrind {tool_name} exit code {rc}",
    )


# ---------------------------------------------------------------------------
# Build graph visualization
# ---------------------------------------------------------------------------

def _cmd_graph(args) -> CLIResult:
    """Generate CMake dependency graph using --graphviz and optionally render with dot."""
    bd_arg = getattr(args, "build_dir", None)
    build_dir = Path(bd_arg) if bd_arg else _find_active_build_dir()
    render: bool = getattr(args, "render", False)
    output_format: str = getattr(args, "format", "svg")

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    graph_file = LOGS_DIR / "dependency_graph.dot"

    # CMake must be re-run with --graphviz pointing to a file
    cache_file = build_dir / "CMakeCache.txt"
    if not cache_file.exists():
        return CLIResult(success=False, code=1, message=f"No CMakeCache.txt in {build_dir}")

    # Extract source dir from CMakeCache
    source_dir = None
    for line in cache_file.read_text(encoding="utf-8").splitlines():
        if line.startswith("CMAKE_HOME_DIRECTORY:INTERNAL="):
            source_dir = line.split("=", 1)[1].strip()
            break

    if not source_dir:
        source_dir = str(PROJECT_ROOT)

    Logger.info(f"Generating dependency graph → {graph_file}")
    cmd = [
        "cmake",
        f"--graphviz={graph_file}",
        "-B", str(build_dir),
        "-S", source_dir,
    ]
    rc = run_proc(cmd, check=False)
    if rc != 0:
        return CLIResult(success=False, code=rc, message="cmake --graphviz failed")

    if not graph_file.exists():
        return CLIResult(success=False, code=1, message=f"Graph file not generated: {graph_file}")

    Logger.info(f"Graph written: {graph_file}")

    if render:
        dot = shutil.which("dot")
        if not dot:
            Logger.warning("graphviz 'dot' not found. Install: sudo apt install graphviz")
            Logger.info(f"  Render manually: dot -T{output_format} {graph_file} -o {LOGS_DIR}/graph.{output_format}")
        else:
            out_img = LOGS_DIR / f"dependency_graph.{output_format}"
            rc2 = run_proc([dot, f"-T{output_format}", str(graph_file), "-o", str(out_img)], check=False)
            if rc2 == 0:
                Logger.info(f"Graph rendered → {out_img}")
            else:
                Logger.error("dot rendering failed")

    return CLIResult(success=True, message=f"Graph: {graph_file}", data={"dot_file": str(graph_file)})


# ---------------------------------------------------------------------------
# Internal helpers shared between commands
# ---------------------------------------------------------------------------

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


def perf_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tool perf", description="Performance analysis tools")
    sub = parser.add_subparsers(dest="subcommand")

    # size
    p = sub.add_parser("size", help="Analyze binary sizes of built artifacts")
    p.add_argument("--build-dir", default=None, dest="build_dir", help="Build directory")
    p.set_defaults(func=_cmd_size)

    # build-time
    p = sub.add_parser("build-time", help="Analyze build times from Ninja log or timed rebuild")
    p.add_argument("--build-dir", default=None, dest="build_dir")
    p.add_argument("--preset", default=None)
    p.set_defaults(func=_cmd_build_time)

    # track
    p = sub.add_parser("track", help="Save current size+build-time as performance baseline")
    p.add_argument("--build-dir", default=None, dest="build_dir")
    p.set_defaults(func=_cmd_track)

    # check-budget
    p = sub.add_parser("check-budget", help="Compare build vs baseline; fail if regressions exceed thresholds")
    p.add_argument("--build-dir", default=None, dest="build_dir")
    p.add_argument("--size-threshold", type=float, default=10.0, metavar="PCT",
                   help="Max allowed size growth %% (default: 10)")
    p.add_argument("--time-threshold", type=float, default=20.0, metavar="PCT",
                   help="Max allowed build time growth %% (default: 20)")
    p.set_defaults(func=_cmd_check_budget)

    # bench
    p = sub.add_parser("bench", help="Discover and run Google Benchmark binaries")
    p.add_argument("--build-dir", default=None, dest="build_dir")
    p.add_argument("--filter", default=None, help="Benchmark filter regex (--benchmark_filter)")
    p.add_argument("--save-baseline", action="store_true", help="Save results as benchmark baseline")
    p.add_argument("--compare", action="store_true", help="Compare against saved benchmark baseline")
    p.set_defaults(func=_cmd_bench)

    # valgrind
    p = sub.add_parser("valgrind", help="Run binary under Valgrind memcheck or massif")
    p.add_argument("--binary", required=True, help="Path to binary (relative to project root or absolute)")
    p.add_argument("--vg-tool", dest="vg_tool", choices=["memcheck", "massif"], default="memcheck")
    p.add_argument("extra_args", nargs=argparse.REMAINDER, help="Extra args passed to the binary")
    p.set_defaults(func=_cmd_valgrind)

    # graph
    p = sub.add_parser("graph", help="Generate CMake dependency graph (.dot)")
    p.add_argument("--build-dir", default=None, dest="build_dir")
    p.add_argument("--render", action="store_true", help="Render to image using 'dot' (graphviz)")
    p.add_argument("--format", default="svg", choices=["svg", "png", "pdf"], help="Image format (default: svg)")
    p.set_defaults(func=_cmd_graph)

    return parser


def main(argv: list[str]) -> None:
    parser = perf_parser()
    args = parser.parse_args(argv if argv else [])
    if hasattr(args, "func"):
        args.func(args).exit()
    else:
        parser.print_help()
