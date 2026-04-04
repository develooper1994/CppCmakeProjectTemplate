"""Profiling subcommands: valgrind, stat, concurrency, vec."""
from __future__ import annotations

import platform
import shutil
import subprocess
from pathlib import Path

from core.utils.common import CLIResult, Logger, PROJECT_ROOT, run_capture, run_proc
from ._helpers import LOGS_DIR, _find_active_build_dir

_IS_LINUX = platform.system() == "Linux"
_IS_MACOS = platform.system() == "Darwin"
_IS_WINDOWS = platform.system() == "Windows"


def _cmd_valgrind(args) -> CLIResult:
    """Run a target binary under Valgrind memcheck or massif."""
    binary: str | None = getattr(args, "binary", None)
    tool_name: str = getattr(args, "vg_tool", "memcheck")
    extra_args: list[str] = getattr(args, "extra_args", []) or []

    if not binary:
        return CLIResult(success=False, code=1, message="Specify binary with --binary <path>")

    valgrind = shutil.which("valgrind")
    if not valgrind:
        # macOS fallback: use `leaks` for memory leak detection
        if _IS_MACOS and tool_name == "memcheck":
            return _cmd_leaks(binary, extra_args)
        hint = (
            "Install: sudo apt install valgrind" if _IS_LINUX
            else "Install: brew install valgrind" if _IS_MACOS
            else "valgrind is not available on Windows — use Dr. Memory or Visual Studio diagnostics"
        )
        return CLIResult(
            success=False, code=1,
            message=f"valgrind not found. {hint}",
        )

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
            "--xml=yes",
            f"--xml-file={xml_out}",
            str(bin_path),
        ] + extra_args
        Logger.info(f"Running memcheck → {xml_out}")

    rc = run_proc(cmd, check=False)

    if tool_name == "massif":
        ms_print = shutil.which("ms_print")
        out_file = LOGS_DIR / "massif.out"
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
# macOS leaks fallback (for valgrind memcheck alternative)
# ---------------------------------------------------------------------------


def _cmd_leaks(binary: str, extra_args: list[str] | None = None) -> CLIResult:
    """Run macOS `leaks` tool as a valgrind memcheck alternative."""
    extra_args = extra_args or []
    leaks_tool = shutil.which("leaks")
    if not leaks_tool:
        return CLIResult(
            success=False, code=1,
            message="macOS 'leaks' tool not found. Install Xcode Command Line Tools.",
        )

    bin_path = Path(binary)
    if not bin_path.is_absolute():
        bin_path = PROJECT_ROOT / binary

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    report = LOGS_DIR / "leaks_report.txt"

    # Run binary, then check for leaks using MallocStackLogging
    env_cmd = ["env", "MallocStackLogging=1"]
    cmd = env_cmd + [str(bin_path)] + extra_args
    Logger.info(f"Running with MallocStackLogging: {bin_path.name}")
    proc = subprocess.run(cmd, capture_output=True, text=True)

    # Now run leaks on the just-finished process (atExit mode)
    leaks_cmd = [leaks_tool, "--atExit", "--", str(bin_path)] + extra_args
    Logger.info(f"Running leaks analysis → {report}")
    result = subprocess.run(leaks_cmd, capture_output=True, text=True)
    output = result.stdout or result.stderr
    report.write_text(output, encoding="utf-8")
    Logger.info(output[:2000])

    rc = result.returncode
    return CLIResult(success=(rc == 0), code=rc, message=f"leaks exit code {rc}")


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
            Logger.info(
                "  Generate flame graph: perf script | stackcollapse-perf.pl | flamegraph.pl > flame.svg"
            )

        rc = result.returncode
    elif _IS_MACOS:
        # macOS: use sample or /usr/bin/time
        time_bin = shutil.which("gtime") or "/usr/bin/time"
        Logger.warn("'perf' not available on macOS — using 'time' fallback.")
        Logger.info("  For detailed profiling, use: xcrun xctrace record --template 'Time Profiler' --launch <binary>")
        cmd = [time_bin, "-l", str(bin_path)] + extra_args if time_bin == "/usr/bin/time" else [time_bin, "-v", str(bin_path)] + extra_args
        result = subprocess.run(cmd, capture_output=True, text=True)
        output = result.stderr or result.stdout
        Logger.info(output)
        report = LOGS_DIR / "time_stat.txt"
        report.write_text(output, encoding="utf-8")
        Logger.info(f"Report saved → {report}")
        rc = result.returncode
    elif _IS_WINDOWS:
        Logger.warn("'perf' is not available on Windows.")
        Logger.info("  Use Visual Studio Diagnostic Tools or Windows Performance Analyzer (WPA) instead.")
        Logger.info("  Or install WSL2 for Linux perf support.")
        return CLIResult(success=False, code=1, message="perf not available on Windows — use VS diagnostics or WPA")
    else:
        # Fallback: GNU time
        time_bin = shutil.which("time") or "/usr/bin/time"
        Logger.warn("'perf' not found — using 'time' fallback. Install: sudo apt install linux-perf")
        cmd = [time_bin, "-v", str(bin_path)] + extra_args
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
        hint = (
            "Install: sudo apt install valgrind" if _IS_LINUX
            else "Install: brew install valgrind" if _IS_MACOS
            else "valgrind is not available on Windows — use TSan or Dr. Memory"
        )
        Logger.warn(f"valgrind not found. {hint}")
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
            flags = [
                "-Rpass=loop-vectorize",
                "-Rpass-missed=loop-vectorize",
                "-Rpass-analysis=loop-vectorize",
            ]
        else:
            flags = ["-fopt-info-vec-missed", "-fopt-info-vec-optimized"]

        cmd = [
            gcc_clang, "-O2", "-std=c++17", "-c", str(source_path),
            "-o", "/dev/null",
        ] + flags
        result = subprocess.run(cmd, capture_output=True, text=True)
        output = result.stderr or result.stdout
        report_file.write_text(output, encoding="utf-8")
        Logger.info(output[:3000] if len(output) > 3000 else output)
        Logger.info(f"Full report → {report_file}")
        return CLIResult(
            success=True,
            message=f"Vectorization report: {report_file}",
            data={"report": str(report_file)},
        )

    return CLIResult(
        success=True,
        message="Vectorization flags shown above. Rebuild to see report.",
        data={},
    )
