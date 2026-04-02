"""Baseline tracking: track, check-budget, bench, compare."""
from __future__ import annotations

import datetime
import json
import subprocess
from pathlib import Path

from core.utils.common import CLIResult, GlobalConfig, Logger, PROJECT_ROOT, run_proc
from ._helpers import (
    BASELINE_FILE,
    BENCH_RESULTS_FILE,
    BUILD_DIR,
    LOGS_DIR,
    _find_active_build_dir,
    _find_binaries,
    _human_size,
    _parse_ninja_log,
    _safe_relative,
)


def _cmd_track(args) -> CLIResult:
    """Capture current size + build-time snapshot as baseline."""
    bd_arg = getattr(args, "build_dir", None)
    build_dir = Path(bd_arg) if bd_arg else _find_active_build_dir()

    # --- size snapshot ---
    binaries = _find_binaries(build_dir)
    size_data: list[dict] = []
    for b in binaries:
        size_data.append({
            "file": _safe_relative(b, PROJECT_ROOT),
            "size_bytes": b.stat().st_size,
        })

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
        "build_dir": _safe_relative(build_dir, PROJECT_ROOT),
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
        return CLIResult(
            success=False, code=1,
            message="No baseline found. Run 'tool perf track' first.",
        )

    baseline = json.loads(BASELINE_FILE.read_text(encoding="utf-8"))
    bd_arg = getattr(args, "build_dir", None)
    build_dir = Path(bd_arg) if bd_arg else _find_active_build_dir()

    size_threshold_pct: float = getattr(args, "size_threshold", None)
    if size_threshold_pct is None:
        size_threshold_pct = GlobalConfig.PERF_SIZE_THRESHOLD_PCT
    time_threshold_pct: float = getattr(args, "time_threshold", None)
    if time_threshold_pct is None:
        time_threshold_pct = GlobalConfig.PERF_TIME_THRESHOLD_PCT

    # --- compare sizes ---
    baseline_sizes = {e["file"]: e["size_bytes"] for e in baseline.get("sizes", [])}
    binaries = _find_binaries(build_dir)
    regressions: list[str] = []
    Logger.info(f"\n{'Artifact':<55} {'Baseline':>12} {'Current':>12} {'Δ%':>8}")
    Logger.info("-" * 92)

    for b in binaries:
        rel = _safe_relative(b, PROJECT_ROOT)
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
            Logger.info(
                f"\nBuild time: baseline={base_time:.2f}s  current={cur_time:.2f}s  "
                f"Δ={delta_pct:+.1f}%{marker}"
            )
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
        return CLIResult(
            success=False, code=1,
            message="Budget check failed",
            data={"regressions": regressions},
        )

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
            message="No benchmark binaries found. Build with ENABLE_BENCHMARKS=ON.",
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
    report = {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "benchmarks": all_results,
    }
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
    baseline_map = {
        b["name"]: b.get("real_time", 0)
        for b in baseline_data.get("benchmarks", [])
    }

    Logger.info(f"\n{'Benchmark':<55} {'Baseline':>12} {'Current':>12} {'Δ%':>8}")
    Logger.info("-" * 92)
    for bm in current:
        name = bm.get("name", "?")
        cur_t = bm.get("real_time", 0)
        if name in baseline_map:
            base_t = baseline_map[name]
            delta = (cur_t - base_t) / base_t * 100 if base_t > 0 else 0.0
            marker = " ⚠" if delta > 10 else ""
            Logger.info(
                f"{name:<55} {base_t:>10.1f} ns {cur_t:>10.1f} ns {delta:>+7.1f}%{marker}"
            )
        else:
            Logger.info(f"{name:<55} {'(new)':>12} {cur_t:>10.1f} ns {'N/A':>8}")
