"""CLI parser and entry point for ``tool perf``."""
from __future__ import annotations

import argparse

from .analysis import _cmd_build_time, _cmd_size, _cmd_size_diff
from .baseline import _cmd_bench, _cmd_check_budget, _cmd_track
from .external import _cmd_godbolt, _cmd_graph
from .profiling import _cmd_concurrency, _cmd_stat, _cmd_valgrind, _cmd_vec, _cmd_uftrace
from .tuning import _cmd_hw_recommend, _cmd_promote, _impl_cmd_autotune


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
    p = sub.add_parser(
        "check-budget",
        help="Compare build vs baseline; fail if regressions exceed thresholds",
    )
    p.add_argument("--build-dir", default=None, dest="build_dir")
    p.add_argument(
        "--size-threshold", type=float, default=10.0, metavar="PCT",
        help="Max allowed size growth %% (default: 10)",
    )
    p.add_argument(
        "--time-threshold", type=float, default=20.0, metavar="PCT",
        help="Max allowed build time growth %% (default: 20)",
    )
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
    p.add_argument(
        "--binary", required=True,
        help="Path to binary (relative to project root or absolute)",
    )
    p.add_argument(
        "--vg-tool", dest="vg_tool", choices=["memcheck", "massif"], default="memcheck",
    )
    p.add_argument("extra_args", nargs=argparse.REMAINDER, help="Extra args passed to the binary")
    p.set_defaults(func=_cmd_valgrind)

    # graph
    p = sub.add_parser("graph", help="Generate CMake dependency graph (.dot)")
    p.add_argument("--build-dir", default=None, dest="build_dir")
    p.add_argument("--render", action="store_true", help="Render to image using 'dot' (graphviz)")
    p.add_argument(
        "--format", default="svg", choices=["svg", "png", "pdf"],
        help="Image format (default: svg)",
    )
    p.set_defaults(func=_cmd_graph)

    # stat  (Linux perf stat / time fallback)
    p = sub.add_parser(
        "stat", help="Profile a binary with 'perf stat' (Linux perf) or 'time' fallback",
    )
    p.add_argument("binary", help="Path to binary (relative to project root or absolute)")
    p.add_argument(
        "--events",
        default="cpu-clock,task-clock,cache-misses,cache-references,instructions,cycles",
        help="Perf events (comma-separated). Default: CPU + cache counters",
    )
    p.add_argument("--repeat", type=int, default=3, help="Number of runs for averaging (default: 3)")
    p.add_argument("--record", action="store_true", help="Also run 'perf record' for flame graph data")
    p.add_argument("extra_args", nargs=argparse.REMAINDER, help="Extra args passed to the binary")
    p.set_defaults(func=_cmd_stat)

    # uftrace
    p = sub.add_parser("uftrace", help="Record and report a uftrace function-level trace")
    p.add_argument("--binary", required=True, help="Path to binary (relative or absolute)")
    p.add_argument("extra_args", nargs=argparse.REMAINDER, help="Extra args passed to the binary")
    p.set_defaults(func=_cmd_uftrace)

    # concurrency  (helgrind / DRD thread-safety analysis)
    p = sub.add_parser(
        "concurrency", help="Analyze thread safety with helgrind or DRD (via Valgrind)",
    )
    p.add_argument("--binary", required=True, help="Path to binary")
    p.add_argument(
        "--tool", dest="conc_tool", choices=["helgrind", "drd"], default="helgrind",
        help="Valgrind concurrency tool (default: helgrind)",
    )
    p.add_argument("extra_args", nargs=argparse.REMAINDER, help="Extra args passed to the binary")
    p.set_defaults(func=_cmd_concurrency)

    # vec  (vectorization report)
    p = sub.add_parser(
        "vec", help="Show vectorization report for a source file (calls CMake rebuild)",
    )
    p.add_argument("--source", required=True, help="Source file path (relative or absolute)")
    p.add_argument("--preset", default=None, help="CMake preset to use for rebuild")
    p.set_defaults(func=_cmd_vec)

    # autotune
    p = sub.add_parser("autotune", help="Sweep compiler flags to find the best combination")
    p.add_argument(
        "--strategy", choices=["hill", "grid", "random", "anneal"], default="hill",
        help="Search strategy: hill (default), grid, random, or anneal",
    )
    p.add_argument(
        "--oracle", choices=["speed", "size", "instructions"], default="speed",
        help="Optimisation goal: speed (cpu_time, default), "
             "size (.text+.data bytes), or instructions (insn count)",
    )
    p.add_argument(
        "--rounds", type=int, default=16, metavar="N",
        help="Maximum number of build+run trials (default: 16)",
    )
    p.add_argument(
        "--filter", default=None, metavar="REGEX",
        help="Benchmark filter regex passed to --benchmark_filter",
    )
    p.add_argument(
        "--T-init", type=float, default=1.0, dest="T_init", metavar="T",
        help="Initial temperature for annealing (default: 1.0)",
    )
    p.add_argument(
        "--T-alpha", type=float, default=0.92, dest="T_alpha", metavar="α",
        help="Cooling rate for annealing 0<α<1 (default: 0.92)",
    )
    p.add_argument(
        "--list-tools", action="store_true", dest="list_tools",
        help="Print available analysis tools and exit",
    )
    p.add_argument(
        "--json", action="store_true",
        help="Print full results JSON to stdout in addition to summary",
    )
    p.add_argument(
        "--repeat", type=int, default=1, metavar="N",
        help="Run oracle N times per trial and use the median score. "
             "Reduces measurement noise (default: 1, no repeat)",
    )
    p.set_defaults(func=_impl_cmd_autotune)

    # promote  (autotune → preset)
    p = sub.add_parser(
        "promote",
        help="Promote autotune-winning flags into a CMakePresets.json entry",
    )
    p.add_argument(
        "--min-improvement", type=float, default=0, metavar="PCT", dest="min_improvement",
        help="Minimum improvement %% vs baseline to promote (default: 0)",
    )
    p.add_argument(
        "--base-preset", default="gcc-release-static-x86_64", dest="base_preset",
        help="Base preset to inherit from (default: gcc-release-static-x86_64)",
    )
    p.add_argument(
        "--dry-run", action="store_true", dest="dry_run",
        help="Preview the preset without writing to CMakePresets.json",
    )
    p.add_argument("--json", action="store_true", help="Print preset JSON to stdout")
    p.set_defaults(func=_cmd_promote)

    # hw-recommend  (hardware-aware flag recommendations)
    p = sub.add_parser(
        "hw-recommend",
        help="Recommend compiler flags based on host CPU capabilities",
    )
    p.add_argument(
        "--json", action="store_true",
        help="Print full CPU info and recommendations as JSON",
    )
    p.set_defaults(func=_cmd_hw_recommend)

    # size-diff
    p = sub.add_parser(
        "size-diff",
        help="Compare .text/.data/.bss sizes vs a saved baseline",
    )
    p.add_argument(
        "--base", default=None, metavar="FILE",
        help="Baseline JSON file (default: build_logs/perf_baseline.json)",
    )
    p.add_argument(
        "--fail-on-growth", type=int, default=None, metavar="BYTES", dest="fail_on_growth",
        help="Exit 1 if total binary growth exceeds BYTES (opt-in)",
    )
    p.add_argument("--json", action="store_true", help="Print full diff JSON to stdout")
    p.set_defaults(func=_cmd_size_diff)

    # godbolt
    p = sub.add_parser(
        "godbolt",
        help="Compile a source file via Godbolt Compiler Explorer and print assembly",
    )
    p.add_argument(
        "--source", required=True,
        help="Source file to compile (relative or absolute path)",
    )
    p.add_argument(
        "--compiler", default=None,
        help="Godbolt compiler ID (e.g. g131, clang1800). Default: auto-select",
    )
    p.add_argument(
        "--flags", default="-O2 -std=c++17",
        help="Compiler flags (default: '-O2 -std=c++17')",
    )
    p.add_argument(
        "--save", action="store_true",
        help="Save the assembly output to build_logs/godbolt_<name>.asm",
    )
    p.add_argument(
        "--json", action="store_true", dest="json_out",
        help="Print raw Godbolt JSON response instead of formatted assembly",
    )
    p.set_defaults(func=_cmd_godbolt)

    return parser


def main(argv: list[str]) -> None:
    parser = perf_parser()
    args = parser.parse_args(argv if argv else [])
    if hasattr(args, "func"):
        args.func(args).exit()
    else:
        parser.print_help()
