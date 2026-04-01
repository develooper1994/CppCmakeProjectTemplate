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
            Logger.warn("No bench baseline found. Run with --save-baseline first.")

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
            Logger.warn("graphviz 'dot' not found. Install: sudo apt install graphviz")
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


# ---------------------------------------------------------------------------
# Linux perf stat / time fallback
# ---------------------------------------------------------------------------

def _cmd_stat(args) -> CLIResult:
    """Profile a binary with 'perf stat' (Linux perf) or 'time' fallback."""
    binary_str: str = args.binary
    events: str = getattr(args, "events", "")
    repeat: int = getattr(args, "repeat", 3)
    record: bool = getattr(args, "record", False)
    extra_args: list[str] = getattr(args, "extra_args", []) or []

    bin_path = Path(binary_str)
    if not bin_path.is_absolute():
        bin_path = PROJECT_ROOT / binary_str
    if not bin_path.exists():
        return CLIResult(success=False, code=1, message=f"Binary not found: {bin_path}")

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    perf_tool = shutil.which("perf")

    if perf_tool:
        cmd = [perf_tool, "stat", f"--repeat={repeat}"]
        if events:
            cmd += ["-e", events]
        cmd += ["--", str(bin_path)] + extra_args
        Logger.info(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        # perf stat writes to stderr
        output = result.stderr or result.stdout
        Logger.info(output)
        report = LOGS_DIR / "perf_stat.txt"
        report.write_text(output, encoding="utf-8")
        Logger.info(f"Report saved → {report}")

        if record:
            data_file = LOGS_DIR / "perf.data"
            rec_cmd = [perf_tool, "record", "-g", "-o", str(data_file), str(bin_path)] + extra_args
            Logger.info(f"\nRecording profile data → {data_file}")
            run_proc(rec_cmd, check=False)
            Logger.info("  Generate flame graph: perf script | stackcollapse-perf.pl | flamegraph.pl > flame.svg")

        rc = result.returncode
    else:
        # Fallback: GNU time
        time_bin = shutil.which("time") or "/usr/bin/time"
        Logger.warn("'perf' not found — using 'time' fallback. Install: sudo apt install linux-perf")
        cmd = [time_bin, "-v", str(bin_path)] + extra_args if shutil.which("time") else \
              ["/usr/bin/time", "-v", str(bin_path)] + extra_args
        result = subprocess.run(cmd, capture_output=True, text=True)
        output = result.stderr or result.stdout
        Logger.info(output)
        report = LOGS_DIR / "time_stat.txt"
        report.write_text(output, encoding="utf-8")
        Logger.info(f"Report saved → {report}")
        rc = result.returncode

    return CLIResult(success=(rc == 0), code=rc, message=f"perf stat exit code {rc}")


# ---------------------------------------------------------------------------
# Thread safety / concurrency analysis
# ---------------------------------------------------------------------------

def _cmd_concurrency(args) -> CLIResult:
    """Analyze thread safety with helgrind or DRD (Valgrind)."""
    binary: str = args.binary
    tool_name: str = getattr(args, "conc_tool", "helgrind")
    extra_args: list[str] = getattr(args, "extra_args", []) or []

    valgrind = shutil.which("valgrind")
    if not valgrind:
        Logger.warn("valgrind not found. Install: sudo apt install valgrind")
        Logger.info("Alternative: build with TSan via 'tool build --sanitizers tsan'")
        return CLIResult(success=False, code=1, message="valgrind not found")

    bin_path = Path(binary)
    if not bin_path.is_absolute():
        bin_path = PROJECT_ROOT / binary
    if not bin_path.exists():
        return CLIResult(success=False, code=1, message=f"Binary not found: {bin_path}")

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    xml_out = LOGS_DIR / f"{tool_name}_report.xml"

    cmd = [
        valgrind,
        f"--tool={tool_name}",
        "--error-exitcode=1",
        "--xml=yes",
        f"--xml-file={xml_out}",
        str(bin_path),
    ] + extra_args

    Logger.info(f"Running {tool_name} on {bin_path.name}...")
    Logger.info(f"Report → {xml_out}")
    rc = run_proc(cmd, check=False)

    msg = f"{tool_name}: {'no issues detected' if rc == 0 else 'issues found — check ' + str(xml_out)}"
    Logger.info(f"\nNote: TSan (build-time) is often faster. Use 'tool build --sanitizers tsan' for CI.")
    return CLIResult(success=(rc == 0), code=rc, message=msg)


# ---------------------------------------------------------------------------
# Vectorization analysis
# ---------------------------------------------------------------------------

def _cmd_vec(args) -> CLIResult:
    """Show vectorization report by rebuilding with -fopt-info-vec / -Rpass=loop-vectorize."""
    source_str: str = args.source
    preset: str | None = getattr(args, "preset", None)

    source_path = Path(source_str)
    if not source_path.is_absolute():
        source_path = PROJECT_ROOT / source_str
    if not source_path.exists():
        return CLIResult(success=False, code=1, message=f"Source file not found: {source_path}")

    # Detect compiler from preset/build dir
    build_dir = _find_active_build_dir()
    cache = build_dir / "CMakeCache.txt"
    compiler = ""
    if cache.exists():
        for line in cache.read_text(encoding="utf-8").splitlines():
            if "CMAKE_CXX_COMPILER:FILEPATH" in line:
                compiler = line.split("=", 1)[-1].strip().lower()
                break

    # Determine flag
    is_clang = "clang" in compiler
    is_gcc = "g++" in compiler or "gcc" in compiler

    if is_clang:
        vec_flag = "-Rpass=loop-vectorize -Rpass-missed=loop-vectorize -Rpass-analysis=loop-vectorize"
        Logger.info("Clang vectorization remarks (Rpass)")
    elif is_gcc:
        vec_flag = "-fopt-info-vec-missed -fopt-info-vec-optimized"
        Logger.info("GCC vectorization info (-fopt-info-vec)")
    else:
        vec_flag = "-fopt-info-vec-missed -fopt-info-vec-optimized"
        Logger.info("Using GCC-style vectorization flags (fallback)")

    Logger.info(f"\nFlags to add to your CMake target:")
    Logger.info(f"  target_compile_options(<target> PRIVATE {vec_flag})")
    Logger.info(f"\nOr rebuild with environment variable:")
    Logger.info(f"  CXXFLAGS='{vec_flag}' cmake --build {build_dir}")

    # Try a direct quick-compile to get vec report
    gcc_clang = shutil.which("clang++") if is_clang else shutil.which("g++")
    if gcc_clang:
        Logger.info(f"\nRunning vectorization analysis on {source_path.name}...")
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        report_file = LOGS_DIR / "vec_report.txt"

        if is_clang:
            flags = ["-Rpass=loop-vectorize", "-Rpass-missed=loop-vectorize",
                     "-Rpass-analysis=loop-vectorize"]
        else:
            flags = ["-fopt-info-vec-missed", "-fopt-info-vec-optimized"]

        cmd = [gcc_clang, "-O2", "-std=c++17", "-c", str(source_path),
               "-o", "/dev/null"] + flags
        result = subprocess.run(cmd, capture_output=True, text=True)
        output = result.stderr or result.stdout
        report_file.write_text(output, encoding="utf-8")
        Logger.info(output[:3000] if len(output) > 3000 else output)
        Logger.info(f"Full report → {report_file}")
        return CLIResult(success=True, message=f"Vectorization report: {report_file}", data={"report": str(report_file)})

    return CLIResult(success=True, message="Vectorization flags shown above. Rebuild to see report.", data={})


# ---------------------------------------------------------------------------
# Compiler-flag auto-tuner — multi-oracle, multi-strategy
# ---------------------------------------------------------------------------

def _detect_available_tools() -> dict:
    """Probe for optional analysis tools. Returns {name: path|None}."""
    tools = ["nm", "size", "objdump", "bloaty", "perf", "valgrind",
             "hyperfine", "gprof"]
    return {t: shutil.which(t) for t in tools}


def _impl_cmd_autotune(args) -> CLIResult:
    """Sweep compiler flags to find the best combination for the chosen oracle.

    Reads ``tool.toml [autotuner].flag_candidates`` (list of lists of strings)
    for the ``speed`` / ``instructions`` oracles, or ``size_flag_candidates``
    for the ``size`` oracle.  Each inner list is a *flag group* — at most one
    flag from each group is active at a time.  Empty string ``""`` means
    "no flag" (the baseline choice).

    Oracles
    -------
    speed        (default) Sums Google Benchmark ``cpu_time`` across all
                 benchmark binaries.  Lower is better (ns).
    size         Sums ``.text + .data`` bytes from ``size --format=berkeley``
                 over built ELF binaries.  Lower is better (bytes).
                 Uses ``bloaty`` as fallback when ``size`` is absent.
    instructions Counts instructions executed via ``perf stat -e instructions``
                 (fallback: ``valgrind --tool=callgrind``).  Lower is better.
                 Falls back to ``speed`` when neither tool is available.

    Strategies
    ----------
    hill  (default)
        Start with the first flag in every group.  Flip one group per
        iteration; keep the change if it lowers the score.  Repeat until no
        improvement or ``--rounds`` budget is exhausted.
    grid
        Enumerate the cartesian product of all flag groups up to ``--rounds``
        trials; pick the combination with the lowest score.
    random
        Sample ``--rounds`` random combinations from the flag space without
        exhaustive enumeration.  Good for large search spaces.
    anneal
        Simulated annealing: accept worse solutions with probability
        exp(-δ / T).  T decreases by ``--T-alpha`` each round.
        Escapes local optima that hill-climb misses.

    Output: ``build_logs/autotune_results.json`` + terminal summary table.
    """
    import itertools
    import math
    import random as _random
    from core.utils.config_loader import load_tool_config

    rounds       = int(getattr(args, "rounds", 16))
    strategy     = getattr(args, "strategy", "hill")
    oracle       = getattr(args, "oracle", "speed")
    bench_filter = getattr(args, "filter", None)
    as_json      = getattr(args, "json", False)
    list_tools   = getattr(args, "list_tools", False)
    t_init       = float(getattr(args, "T_init", 1.0))
    t_alpha      = float(getattr(args, "T_alpha", 0.92))

    # ── Tool detection ─────────────────────────────────────────────────────
    available = _detect_available_tools()

    if list_tools:
        Logger.info("Available analysis tools:")
        for name, path in sorted(available.items()):
            status = path if path else "(not found)"
            Logger.info(f"  {name:<12} {status}")
        return CLIResult(success=True, message="Tool list shown above", data=available)

    # ── Oracle validation / fallback ───────────────────────────────────────
    if oracle == "size":
        if not available.get("size") and not available.get("bloaty"):
            Logger.error("oracle=size requires 'size' (binutils) or 'bloaty'. "
                         "Neither was found on PATH.")
            return CLIResult(success=False, code=1, message="No size tool available")
    elif oracle == "instructions":
        if not available.get("perf") and not available.get("valgrind"):
            Logger.warn("oracle=instructions: neither 'perf' nor 'valgrind' found — "
                        "falling back to speed oracle")
            oracle = "speed"

    # ── Load [autotuner] from tool.toml ────────────────────────────────────
    cfg = load_tool_config()
    at_cfg: dict = cfg.get("autotuner", {})

    # Honour T_init / T_alpha from tool.toml when not overridden
    t_init  = float(at_cfg.get("T_init",  t_init))
    t_alpha = float(at_cfg.get("T_alpha", t_alpha))

    # Select flag candidates based on oracle
    if oracle == "size":
        flag_groups: list[list[str]] = at_cfg.get(
            "size_flag_candidates", at_cfg.get("flag_candidates", []))
    else:
        flag_groups = at_cfg.get("flag_candidates", [])

    if not flag_groups:
        Logger.error("No flag_candidates defined in tool.toml [autotuner]. "
                     "Add a section like:\n  [autotuner]\n  flag_candidates = [[\"-O2\",\"-O3\"],[...]]")
        return CLIResult(success=False, code=1, message="No flag_candidates configured")

    AUTOTUNE_DIR = BUILD_DIR / "autotune"
    AUTOTUNE_DIR.mkdir(parents=True, exist_ok=True)

    # ── Oracle implementations ──────────────────────────────────────────────

    def _oracle_speed(bench_bins: list, bench_filter) -> "float | None":
        """Sum cpu_time across all benchmarks. Lower is better (ns)."""
        total = 0.0
        for bb in bench_bins:
            bench_cmd = [str(bb), "--benchmark_format=json", "--benchmark_min_time=0.1"]
            if bench_filter:
                bench_cmd.append(f"--benchmark_filter={bench_filter}")
            try:
                r = subprocess.run(bench_cmd, capture_output=True, text=True, timeout=180)
                if r.returncode == 0 and r.stdout.strip():
                    data = json.loads(r.stdout)
                    for bm in data.get("benchmarks", []):
                        total += bm.get("cpu_time", 0.0)
            except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as exc:
                Logger.warn(f"    Benchmark error: {exc}")
        return total if total > 0.0 else None

    def _oracle_size(trial_dir: Path, bench_bins: list) -> "float | None":
        """Sum .text+.data bytes. Lower is better (bytes)."""
        size_bin  = available.get("size")
        bloaty_bin = available.get("bloaty")
        targets   = list(bench_bins)

        # Fall back to all ELF executables in the trial dir when bench bins absent
        if not targets:
            for p in trial_dir.rglob("*"):
                if p.is_file() and (p.stat().st_mode & 0o111):
                    try:
                        with open(p, "rb") as fh:
                            if fh.read(4) == b"\x7fELF":
                                targets.append(p)
                    except OSError:
                        pass

        total_bytes = 0
        for t in targets:
            if size_bin:
                try:
                    r = subprocess.run(
                        [size_bin, "--format=berkeley", str(t)],
                        capture_output=True, text=True, timeout=15)
                    if r.returncode == 0:
                        for line in r.stdout.splitlines():
                            parts = line.split()
                            # berkeley output: text  data  bss  dec  hex  filename
                            if len(parts) >= 4 and parts[0].isdigit():
                                total_bytes += int(parts[0]) + int(parts[1])
                except (subprocess.TimeoutExpired, OSError, ValueError) as exc:
                    Logger.warn(f"    size error: {exc}")
            elif bloaty_bin:
                try:
                    r = subprocess.run(
                        [bloaty_bin, "-n", "0", "--csv", str(t)],
                        capture_output=True, text=True, timeout=30)
                    if r.returncode == 0:
                        for line in r.stdout.splitlines()[1:]:  # skip header
                            parts = line.split(",")
                            if len(parts) >= 2:
                                try:
                                    total_bytes += int(parts[-1])
                                except ValueError:
                                    pass
                except (subprocess.TimeoutExpired, OSError) as exc:
                    Logger.warn(f"    bloaty error: {exc}")

        return float(total_bytes) if total_bytes > 0 else None

    def _oracle_instructions(bench_bins: list, bench_filter) -> "float | None":
        """Count instructions executed. Lower is better."""
        perf_bin    = available.get("perf")
        valgrind_bin = available.get("valgrind")
        total_insn  = 0.0

        for bb in bench_bins:
            bench_args = [str(bb), "--benchmark_min_time=0.05"]
            if bench_filter:
                bench_args.append(f"--benchmark_filter={bench_filter}")

            if perf_bin:
                cmd = [perf_bin, "stat", "-e", "instructions", "--"] + bench_args
                try:
                    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                    combined = r.stderr + r.stdout
                    for line in combined.splitlines():
                        if "instructions" in line:
                            for token in line.split():
                                cleaned = token.replace(",", "")
                                if cleaned.isdigit():
                                    total_insn += float(cleaned)
                                    break
                except (subprocess.TimeoutExpired, OSError) as exc:
                    Logger.warn(f"    perf stat error: {exc}")
            elif valgrind_bin:
                cmd = [valgrind_bin, "--tool=callgrind",
                       "--callgrind-out-file=/dev/null", "--"] + bench_args
                try:
                    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                    for line in (r.stderr + r.stdout).splitlines():
                        if "I refs:" in line or "Ir " in line:
                            for token in line.split():
                                cleaned = token.replace(",", "")
                                if cleaned.isdigit():
                                    total_insn += float(cleaned)
                                    break
                except (subprocess.TimeoutExpired, OSError) as exc:
                    Logger.warn(f"    valgrind error: {exc}")

        return total_insn if total_insn > 0.0 else None

    # ── Build + score helper ───────────────────────────────────────────────

    def _score_flags(flags: list, trial_name: str) -> "float | None":
        """Configure, build, then evaluate with the selected oracle."""
        trial_dir = AUTOTUNE_DIR / trial_name
        flags_str = " ".join(f for f in flags if f)
        Logger.info(f"  [{trial_name}] oracle={oracle} "
                    f"CXX_FLAGS=[{flags_str or '(defaults)'}]")

        cfg_cmd = [
            "cmake",
            "-S", str(PROJECT_ROOT),
            "-B", str(trial_dir),
            "-DCMAKE_BUILD_TYPE=Release",
            f"-DCMAKE_CXX_FLAGS={flags_str}",
            "-DENABLE_BENCHMARKS=ON",
            "-DBUILD_TESTING=OFF",
            "-DBUILD_SHARED_LIBS=OFF",
        ]
        r = subprocess.run(cfg_cmd, capture_output=True, text=True, cwd=PROJECT_ROOT)
        if r.returncode != 0:
            Logger.warn(f"    Configure failed: {r.stderr[-300:].strip()}")
            return None

        bld_cmd = ["cmake", "--build", str(trial_dir), "--parallel"]
        r = subprocess.run(bld_cmd, capture_output=True, text=True, cwd=PROJECT_ROOT)
        if r.returncode != 0:
            Logger.warn(f"    Build failed: {r.stderr[-300:].strip()}")
            return None

        # Discover ELF benchmark binaries
        bench_bins: list[Path] = []
        for p in trial_dir.rglob("*"):
            if not p.is_file():
                continue
            name = p.name.lower()
            if ("bench" in name or "benchmark" in name) and (p.stat().st_mode & 0o111):
                try:
                    with open(p, "rb") as fh:
                        if fh.read(4) == b"\x7fELF":
                            bench_bins.append(p)
                except OSError:
                    pass

        if oracle in ("speed", "instructions") and not bench_bins:
            Logger.warn("    No benchmark binaries found. Build with ENABLE_BENCHMARKS=ON.")
            return None

        if oracle == "speed":
            return _oracle_speed(bench_bins, bench_filter)
        elif oracle == "size":
            return _oracle_size(trial_dir, bench_bins)
        elif oracle == "instructions":
            return _oracle_instructions(bench_bins, bench_filter)
        return None

    # ── Run selected strategy ──────────────────────────────────────────────
    results: list[dict] = []
    best_flags: list[str] = [g[0] for g in flag_groups]
    best_score: float = float("inf")
    oracle_unit = {
        "speed":        "ns (cpu_time, ↓)",
        "size":         "bytes (.text+.data, ↓)",
        "instructions": "insn (↓)",
    }.get(oracle, "score (↓)")

    if strategy == "hill":
        Logger.info(f"Autotune: hill-climb  oracle={oracle}")
        score = _score_flags(best_flags, "baseline")
        if score is None:
            return CLIResult(success=False, code=1, message="Baseline build/run failed")
        best_score = score
        results.append({"trial": "baseline", "flags": list(best_flags), "score": best_score})
        Logger.info(f"  Baseline: {best_score:.1f} {oracle_unit}")

        iteration = 0
        improved = True
        while improved and iteration < rounds:
            improved = False
            for gi, group in enumerate(flag_groups):
                for alt_flag in group[1:]:
                    if iteration >= rounds:
                        break
                    trial_flags = list(best_flags)
                    trial_flags[gi] = alt_flag
                    trial_name = f"hill_{iteration:02d}"
                    new_score = _score_flags(trial_flags, trial_name)
                    iteration += 1
                    if new_score is not None:
                        results.append({
                            "trial": trial_name,
                            "flags": trial_flags,
                            "score": new_score,
                        })
                        if new_score < best_score:
                            best_score = new_score
                            best_flags = trial_flags
                            improved = True
                            Logger.info(f"  ↑ Improved → {best_score:.1f}  flags={trial_flags}")

    elif strategy == "grid":
        Logger.info(f"Autotune: grid search  oracle={oracle}")
        combos = list(itertools.product(*flag_groups))[:rounds]
        for i, combo in enumerate(combos):
            trial_flags = list(combo)
            new_score = _score_flags(trial_flags, f"grid_{i:02d}")
            if new_score is not None:
                results.append({
                    "trial": f"grid_{i:02d}",
                    "flags": trial_flags,
                    "score": new_score,
                })
                if new_score < best_score:
                    best_score = new_score
                    best_flags = trial_flags
                    Logger.info(f"  Best so far → {best_score:.1f}  flags={trial_flags}")

    elif strategy == "random":
        Logger.info(f"Autotune: random sampling  oracle={oracle}  rounds={rounds}")
        seen: set = set()
        attempts = 0
        max_attempts = rounds * 5
        while len(results) < rounds and attempts < max_attempts:
            attempts += 1
            combo = [_random.choice(g) for g in flag_groups]
            key = tuple(combo)
            if key in seen:
                continue
            seen.add(key)
            trial_name = f"rand_{len(results):02d}"
            new_score = _score_flags(combo, trial_name)
            if new_score is not None:
                results.append({"trial": trial_name, "flags": combo, "score": new_score})
                if new_score < best_score:
                    best_score = new_score
                    best_flags = combo
                    Logger.info(f"  ↑ New best → {best_score:.1f}  flags={combo}")

    elif strategy == "anneal":
        Logger.info(f"Autotune: simulated annealing  oracle={oracle}  "
                    f"T={t_init}  α={t_alpha}")
        current_flags = [_random.choice(g) for g in flag_groups]
        score = _score_flags(current_flags, "anneal_init")
        if score is None:
            return CLIResult(success=False, code=1,
                             message="Initial build/run failed for annealing")
        current_score = score
        best_score    = current_score
        best_flags    = list(current_flags)
        results.append({
            "trial": "anneal_init",
            "flags": list(current_flags),
            "score": current_score,
        })
        T = t_init
        for i in range(rounds):
            gi = _random.randrange(len(flag_groups))
            new_flags = list(current_flags)
            new_flags[gi] = _random.choice(flag_groups[gi])
            trial_name = f"anneal_{i:02d}"
            new_score = _score_flags(new_flags, trial_name)
            if new_score is None:
                T *= t_alpha
                continue
            results.append({"trial": trial_name, "flags": new_flags, "score": new_score})
            delta = new_score - current_score
            # Accept if better, or with Boltzmann probability if worse
            if delta < 0 or _random.random() < math.exp(-delta / (T * current_score + 1e-9)):
                current_flags = new_flags
                current_score = new_score
                if new_score < best_score:
                    best_score = new_score
                    best_flags = new_flags
                    Logger.info(f"  ↑ New best (T={T:.3f}) → {best_score:.1f}  flags={new_flags}")
            T *= t_alpha

    else:
        return CLIResult(
            success=False, code=1,
            message=f"Unknown strategy: {strategy!r}. "
                    "Use hill, grid, random, or anneal.")

    # ── Persist + report ───────────────────────────────────────────────────
    results.sort(key=lambda e: e.get("score", float("inf")))
    best_flag_str = " ".join(f for f in best_flags if f) or "(defaults)"
    output = {
        "strategy":   strategy,
        "oracle":     oracle,
        "best_flags": best_flags,
        "best_score": best_score if best_score < float("inf") else None,
        "trials":     results,
    }
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    out_file = LOGS_DIR / "autotune_results.json"
    out_file.write_text(json.dumps(output, indent=2), encoding="utf-8")

    Logger.info(f"\nAutotune complete — {len(results)} trial(s) run.")
    Logger.info(f"Oracle     : {oracle} ({oracle_unit})")
    Logger.info(f"Best flags : {best_flag_str}")
    if best_score < float("inf"):
        Logger.info(f"Best score : {best_score:.1f} {oracle_unit}")
    else:
        Logger.info("Best score : N/A (all trials failed)")
    Logger.info(f"Results    → {out_file}")

    Logger.info(f"\n{'Trial':<15} {'Flags':<45} {'Score':>12}")
    Logger.info("-" * 75)
    for entry in results[:10]:
        flag_str = " ".join(f for f in entry["flags"] if f) or "(defaults)"
        score_s  = f"{entry['score']:.1f}" if entry.get("score") is not None else "N/A"
        Logger.info(f"{entry['trial']:<15} {flag_str:<45} {score_s:>12}")

    if as_json:
        print(json.dumps(output, indent=2))

    return CLIResult(success=True, message="Autotune complete", data=output)



# ---------------------------------------------------------------------------
# Binary size delta tracking
# ---------------------------------------------------------------------------

def _cmd_size_diff(args) -> CLIResult:
    """Compare .text/.data/.bss section sizes between current build and baseline.

    Reads ``build_logs/perf_baseline.json`` (saved by ``tool perf track``) as
    the *base* snapshot and compares it against the current build artifacts
    using ``size --format=berkeley``.  Pass ``--base <file>`` to override the
    baseline path.
    """
    import re as _re

    base_file  = getattr(args, "base", None)
    fail_bytes = getattr(args, "fail_on_growth", None)
    as_json    = getattr(args, "json", False)

    size_bin = shutil.which("size")
    if not size_bin:
        Logger.error("'size' (binutils) is required for size-diff but was not found on PATH.")
        return CLIResult(success=False, code=1, message="'size' tool not found")

    # ── Load baseline ──────────────────────────────────────────────────────
    baseline_path = Path(base_file) if base_file else LOGS_DIR / "perf_baseline.json"
    if not baseline_path.exists():
        Logger.error(f"Baseline file not found: {baseline_path}\n"
                     "Run 'tool perf track' first to save a baseline.")
        return CLIResult(success=False, code=1, message="No baseline file found")

    try:
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return CLIResult(success=False, code=1,
                         message=f"Cannot read baseline: {exc}")

    base_sizes: dict = baseline.get("sizes", {})

    # ── Collect current sizes ──────────────────────────────────────────────
    active_build = _find_active_build_dir()
    elf_binaries: list[Path] = _find_binaries(active_build)

    head_sizes: dict = {}
    for p in elf_binaries:
        r = subprocess.run(
            [size_bin, "--format=berkeley", str(p)],
            capture_output=True, text=True, timeout=15)
        if r.returncode != 0:
            continue
        for line in r.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 4 and parts[0].isdigit():
                head_sizes[p.name] = {
                    ".text":  int(parts[0]),
                    ".data":  int(parts[1]),
                    ".bss":   int(parts[2]),
                    "total":  int(parts[0]) + int(parts[1]) + int(parts[2]),
                }

    if not head_sizes:
        Logger.warn("No ELF binaries measured in current build. Run 'tool build' first.")

    # ── Diff ───────────────────────────────────────────────────────────────
    all_names = sorted(set(base_sizes) | set(head_sizes))
    diffs: list[dict] = []
    total_growth = 0

    for name in all_names:
        b = base_sizes.get(name, {})
        h = head_sizes.get(name, {})
        if not b and not h:
            continue
        delta_text  = h.get(".text",  0) - b.get(".text",  0)
        delta_data  = h.get(".data",  0) - b.get(".data",  0)
        delta_bss   = h.get(".bss",   0) - b.get(".bss",   0)
        delta_total = h.get("total",  0) - b.get("total",  0)
        diffs.append({
            "name":         name,
            "base_total":   b.get("total", 0),
            "head_total":   h.get("total", 0),
            "delta_text":   delta_text,
            "delta_data":   delta_data,
            "delta_bss":    delta_bss,
            "delta_total":  delta_total,
        })
        if delta_total > 0:
            total_growth += delta_total

    # ── Display ────────────────────────────────────────────────────────────
    Logger.info(f"\nsize-diff  baseline={baseline_path.name}  build={active_build.name}")
    Logger.info(f"\n{'Binary':<30} {'Base':>10} {'Head':>10} "
                f"{'Δ total':>10} {'Δ .text':>10}")
    Logger.info("-" * 75)
    for d in diffs:
        def _fmt(v):
            return ("+" if v >= 0 else "") + str(v)
        Logger.info(f"{d['name']:<30} {d['base_total']:>10} {d['head_total']:>10} "
                    f"{_fmt(d['delta_total']):>10} {_fmt(d['delta_text']):>10}")

    Logger.info(f"\nTotal binary growth: {'+' if total_growth >= 0 else ''}"
                f"{total_growth} bytes (.text+.data+.bss)")

    output = {
        "baseline": str(baseline_path),
        "build_dir": str(active_build),
        "total_growth_bytes": total_growth,
        "binaries": diffs,
    }
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    (LOGS_DIR / "size_report.json").write_text(json.dumps(output, indent=2), encoding="utf-8")

    if as_json:
        print(json.dumps(output, indent=2))

    if fail_bytes is not None and total_growth > fail_bytes:
        return CLIResult(
            success=False, code=1,
            message=f"Binary growth {total_growth}B exceeds --fail-on-growth {fail_bytes}B",
            data=output)

    return CLIResult(success=True,
                     message=f"size-diff complete. Total growth: {total_growth}B",
                     data=output)


def _cmd_godbolt(args: argparse.Namespace) -> CLIResult:
    """Entry point for `tool perf godbolt`."""
    try:
        _impl_godbolt(args)
        return CLIResult(success=True, message="Godbolt compile complete.")
    except SystemExit as e:
        return CLIResult(success=(e.code == 0), code=e.code or 1, message="Godbolt failed.")


def _impl_godbolt(args) -> None:
    """Compile a source file via the Godbolt Compiler Explorer REST API.

    Sends the source to https://godbolt.org/api/compiler/<id>/compile and
    prints the resulting assembly to stdout.  When --save is set the output
    is also written to build_logs/godbolt_<basename>.asm.

    Compiler IDs: g131 = GCC 13.1, clang1800 = Clang 18.0.0, etc.
    Full list: curl -s https://godbolt.org/api/compilers | python3 -m json.tool | grep '"id"'
    """
    import urllib.request
    import urllib.error

    src_path = Path(args.source)
    if not src_path.is_absolute():
        src_path = PROJECT_ROOT / src_path
    if not src_path.exists():
        Logger.error(f"Source file not found: {src_path}")
        raise SystemExit(1)

    source_code = src_path.read_text(encoding="utf-8")
    flags: str = getattr(args, "flags", "-O2 -std=c++17") or "-O2 -std=c++17"
    compiler_id: str = getattr(args, "compiler", None) or "g131"
    save: bool = getattr(args, "save", False)
    json_out: bool = getattr(args, "json_out", False)

    url = f"https://godbolt.org/api/compiler/{compiler_id}/compile"
    payload = json.dumps({
        "source": source_code,
        "options": {
            "userArguments": flags,
            "compilerOptions": {},
            "filters": {
                "binary": False,
                "commentOnly": True,
                "demangle": True,
                "directives": True,
                "intel": True,
                "labels": True,
                "trim": True,
            },
        },
        "lang": "c++",
    }).encode("utf-8")

    Logger.info(f"[Godbolt] Compiling '{src_path.name}' with compiler '{compiler_id}' flags '{flags}'")
    Logger.info(f"[Godbolt] Endpoint: {url}")

    try:
        req = urllib.request.Request(
            url, data=payload,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        Logger.error(f"[Godbolt] HTTP {e.code}: {e.reason}")
        raise SystemExit(1)
    except urllib.error.URLError as e:
        Logger.error(f"[Godbolt] Network error: {e.reason}. Check internet connectivity.")
        raise SystemExit(1)

    if json_out:
        print(body)
        return

    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        Logger.error("[Godbolt] Failed to parse response JSON.")
        print(body)
        raise SystemExit(1)

    # Format the assembly output
    asm_lines = data.get("asm", [])
    stderr_lines = data.get("stderr", [])
    stdout_lines = data.get("stdout", [])
    exit_code = data.get("code", 0)

    if stdout_lines:
        print("──── stdout ────")
        for line in stdout_lines:
            print(line.get("text", ""))
    if stderr_lines:
        print("──── stderr ────")
        for line in stderr_lines:
            print(line.get("text", ""))

    if not asm_lines:
        Logger.warn("[Godbolt] No assembly output returned (compilation may have failed).")
        if exit_code != 0:
            Logger.error(f"[Godbolt] Compiler exited with code {exit_code}")
            raise SystemExit(1)
        return

    asm_text = "\n".join(line.get("text", "") for line in asm_lines)
    print("\n──── assembly ────")
    print(asm_text)

    if save:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        out_file = LOGS_DIR / f"godbolt_{src_path.stem}.asm"
        header = (
            f"; Godbolt Compiler Explorer output\n"
            f"; Source   : {src_path}\n"
            f"; Compiler : {compiler_id}\n"
            f"; Flags    : {flags}\n\n"
        )
        out_file.write_text(header + asm_text, encoding="utf-8")
        Logger.success(f"[Godbolt] Assembly saved to {out_file}")


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

    # stat  (Linux perf stat / time fallback)
    p = sub.add_parser("stat", help="Profile a binary with 'perf stat' (Linux perf) or 'time' fallback")
    p.add_argument("binary", help="Path to binary (relative to project root or absolute)")
    p.add_argument("--events", default="cpu-clock,task-clock,cache-misses,cache-references,instructions,cycles",
                   help="Perf events (comma-separated). Default: CPU + cache counters")
    p.add_argument("--repeat", type=int, default=3, help="Number of runs for averaging (default: 3)")
    p.add_argument("--record", action="store_true", help="Also run 'perf record' for flame graph data")
    p.add_argument("extra_args", nargs=argparse.REMAINDER, help="Extra args passed to the binary")
    p.set_defaults(func=_cmd_stat)

    # concurrency  (helgrind / DRD thread-safety analysis)
    p = sub.add_parser("concurrency", help="Analyze thread safety with helgrind or DRD (via Valgrind)")
    p.add_argument("--binary", required=True, help="Path to binary")
    p.add_argument("--tool", dest="conc_tool", choices=["helgrind", "drd"], default="helgrind",
                   help="Valgrind concurrency tool (default: helgrind)")
    p.add_argument("extra_args", nargs=argparse.REMAINDER, help="Extra args passed to the binary")
    p.set_defaults(func=_cmd_concurrency)

    # vec  (vectorization report)
    p = sub.add_parser("vec", help="Show vectorization report for a source file (calls CMake rebuild)")
    p.add_argument("--source", required=True, help="Source file path (relative or absolute)")
    p.add_argument("--preset", default=None, help="CMake preset to use for rebuild")
    p.set_defaults(func=_cmd_vec)

    # autotune
    p = sub.add_parser("autotune",
                       help="Sweep compiler flags to find the best combination")
    p.add_argument("--strategy",
                   choices=["hill", "grid", "random", "anneal"],
                   default="hill",
                   help="Search strategy: hill (default), grid, random, or anneal")
    p.add_argument("--oracle",
                   choices=["speed", "size", "instructions"],
                   default="speed",
                   help="Optimisation goal: speed (cpu_time, default), "
                        "size (.text+.data bytes), or instructions (insn count)")
    p.add_argument("--rounds", type=int, default=16, metavar="N",
                   help="Maximum number of build+run trials (default: 16)")
    p.add_argument("--filter", default=None, metavar="REGEX",
                   help="Benchmark filter regex passed to --benchmark_filter")
    p.add_argument("--T-init",  type=float, default=1.0,  dest="T_init",
                   metavar="T",
                   help="Initial temperature for annealing (default: 1.0)")
    p.add_argument("--T-alpha", type=float, default=0.92, dest="T_alpha",
                   metavar="α",
                   help="Cooling rate for annealing 0<α<1 (default: 0.92)")
    p.add_argument("--list-tools", action="store_true", dest="list_tools",
                   help="Print available analysis tools and exit")
    p.add_argument("--json", action="store_true",
                   help="Print full results JSON to stdout in addition to summary")
    p.set_defaults(func=_impl_cmd_autotune)

    # size-diff
    p = sub.add_parser("size-diff",
                       help="Compare .text/.data/.bss sizes vs a saved baseline")
    p.add_argument("--base", default=None, metavar="FILE",
                   help="Baseline JSON file (default: build_logs/perf_baseline.json)")
    p.add_argument("--fail-on-growth", type=int, default=None,
                   metavar="BYTES", dest="fail_on_growth",
                   help="Exit 1 if total binary growth exceeds BYTES (opt-in)")
    p.add_argument("--json", action="store_true",
                   help="Print full diff JSON to stdout")
    p.set_defaults(func=_cmd_size_diff)

    # godbolt
    p = sub.add_parser("godbolt",
                       help="Compile a source file via Godbolt Compiler Explorer and print assembly")
    p.add_argument("--source", required=True,
                   help="Source file to compile (relative or absolute path)")
    p.add_argument("--compiler", default=None,
                   help="Godbolt compiler ID (e.g. g131, clang1800). Default: auto-select")
    p.add_argument("--flags", default="-O2 -std=c++17",
                   help="Compiler flags (default: '-O2 -std=c++17')")
    p.add_argument("--save", action="store_true",
                   help="Save the assembly output to build_logs/godbolt_<name>.asm")
    p.add_argument("--json", action="store_true", dest="json_out",
                   help="Print raw Godbolt JSON response instead of formatted assembly")
    p.set_defaults(func=_cmd_godbolt)

    return parser


def main(argv: list[str]) -> None:
    parser = perf_parser()
    args = parser.parse_args(argv if argv else [])
    if hasattr(args, "func"):
        args.func(args).exit()
    else:
        parser.print_help()
