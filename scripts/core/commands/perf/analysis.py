"""Analysis subcommands: size, size-diff, build-time."""
from __future__ import annotations

import json
import shutil
import subprocess
import time
from pathlib import Path

from core.utils.common import CLIResult, Logger, PROJECT_ROOT, run_capture, run_proc
from ._helpers import (
    BUILD_DIR,
    LOGS_DIR,
    _find_active_build_dir,
    _find_binaries,
    _human_size,
    _parse_ninja_log,
    _safe_relative,
)


def _cmd_size(args) -> CLIResult:
    """Analyze binary sizes of built artifacts."""
    bd_arg = getattr(args, "build_dir", None)
    build_dir = Path(bd_arg) if bd_arg else _find_active_build_dir()

    binaries = _find_binaries(build_dir)

    if not binaries:
        return CLIResult(
            success=False, code=1,
            message=f"No binaries found in {build_dir}/bin or {build_dir}/lib",
        )

    size_tool = shutil.which("size")
    bloaty_tool = shutil.which("bloaty")

    results = []
    for b in binaries:
        stat = b.stat()
        entry = {
            "file": _safe_relative(b, PROJECT_ROOT),
            "size_bytes": stat.st_size,
            "size_human": _human_size(stat.st_size),
        }

        if size_tool:
            try:
                out, rc = run_capture([size_tool, "--format=berkeley", str(b)])
                if rc == 0:
                    entry["sections"] = out.strip()
            except Exception:
                pass

        results.append(entry)

    Logger.info(f"{'File':<50} {'Size':>12}")
    Logger.info("-" * 64)
    for r in results:
        Logger.info(f"{r['file']:<50} {r['size_human']:>12}")

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
    bd_arg = getattr(args, "build_dir", None)
    build_dir = Path(bd_arg) if bd_arg else _find_active_build_dir()
    preset = getattr(args, "preset", None)

    ninja_log = build_dir / ".ninja_log"
    if ninja_log.exists():
        return _analyze_ninja_log(ninja_log)

    time_traces = list(build_dir.rglob("*.json"))
    time_traces = [t for t in time_traces if "time-trace" in t.name.lower()]

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
    report.write_text(
        json.dumps({"total_seconds": round(total, 2), "targets": entries}, indent=2),
        encoding="utf-8",
    )
    Logger.info(f"Report: {report}")

    return CLIResult(success=True, message=f"Build time analysis: {total:.2f}s total", data=entries)


def _cmd_size_diff(args) -> CLIResult:
    """Compare .text/.data/.bss section sizes between current build and baseline."""
    base_file = getattr(args, "base", None)
    fail_bytes = getattr(args, "fail_on_growth", None)
    as_json = getattr(args, "json", False)

    size_bin = shutil.which("size")
    if not size_bin:
        Logger.error("'size' (binutils) is required for size-diff but was not found on PATH.")
        return CLIResult(success=False, code=1, message="'size' tool not found")

    baseline_path = Path(base_file) if base_file else LOGS_DIR / "perf_baseline.json"
    if not baseline_path.exists():
        Logger.error(
            f"Baseline file not found: {baseline_path}\n"
            "Run 'tool perf track' first to save a baseline."
        )
        return CLIResult(success=False, code=1, message="No baseline file found")

    try:
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return CLIResult(success=False, code=1, message=f"Cannot read baseline: {exc}")

    base_sizes: dict = {}
    raw_sizes = baseline.get("sizes", {})
    if isinstance(raw_sizes, list):
        for entry in raw_sizes:
            fname = Path(entry.get("file", "")).name
            total = entry.get("size_bytes", 0)
            base_sizes[fname] = {".text": 0, ".data": 0, ".bss": 0, "total": total}
    elif isinstance(raw_sizes, dict):
        base_sizes = raw_sizes
    else:
        base_sizes = {}

    active_build = _find_active_build_dir()
    elf_binaries: list[Path] = _find_binaries(active_build)

    head_sizes: dict = {}
    for p in elf_binaries:
        r = subprocess.run(
            [size_bin, "--format=berkeley", str(p)],
            capture_output=True, text=True, timeout=15,
        )
        if r.returncode != 0:
            continue
        for line in r.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 4 and parts[0].isdigit():
                head_sizes[p.name] = {
                    ".text": int(parts[0]),
                    ".data": int(parts[1]),
                    ".bss": int(parts[2]),
                    "total": int(parts[0]) + int(parts[1]) + int(parts[2]),
                }

    if not head_sizes:
        Logger.warn("No ELF binaries measured in current build. Run 'tool build' first.")

    all_names = sorted(set(base_sizes) | set(head_sizes))
    diffs: list[dict] = []
    total_growth = 0

    for name in all_names:
        b = base_sizes.get(name, {})
        h = head_sizes.get(name, {})
        if not b and not h:
            continue
        delta_text = h.get(".text", 0) - b.get(".text", 0)
        delta_data = h.get(".data", 0) - b.get(".data", 0)
        delta_bss = h.get(".bss", 0) - b.get(".bss", 0)
        delta_total = h.get("total", 0) - b.get("total", 0)
        diffs.append({
            "name": name,
            "base_total": b.get("total", 0),
            "head_total": h.get("total", 0),
            "delta_text": delta_text,
            "delta_data": delta_data,
            "delta_bss": delta_bss,
            "delta_total": delta_total,
        })
        if delta_total > 0:
            total_growth += delta_total

    Logger.info(f"\nsize-diff  baseline={baseline_path.name}  build={active_build.name}")
    Logger.info(
        f"\n{'Binary':<30} {'Base':>10} {'Head':>10} "
        f"{'Δ total':>10} {'Δ .text':>10}"
    )
    Logger.info("-" * 75)
    for d in diffs:
        def _fmt(v):
            return ("+" if v >= 0 else "") + str(v)

        Logger.info(
            f"{d['name']:<30} {d['base_total']:>10} {d['head_total']:>10} "
            f"{_fmt(d['delta_total']):>10} {_fmt(d['delta_text']):>10}"
        )

    Logger.info(
        f"\nTotal binary growth: {'+' if total_growth >= 0 else ''}"
        f"{total_growth} bytes (.text+.data+.bss)"
    )

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
            data=output,
        )

    return CLIResult(
        success=True,
        message=f"size-diff complete. Total growth: {total_growth}B",
        data=output,
    )
