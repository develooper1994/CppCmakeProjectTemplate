"""core.commands.perf — Performance analysis tools (package).

Re-exports public API so that ``from core.commands.perf import X`` keeps
working for callers and tests that relied on the old single-module layout.
"""
from __future__ import annotations

from .cli import main, perf_parser

# Helpers used by tests and external callers
from ._helpers import (
    BUILD_DIR,
    LOGS_DIR,
    BASELINE_FILE,
    BENCH_RESULTS_FILE,
    _find_active_build_dir,
    _find_binaries,
    _human_size,
    _parse_ninja_log,
    _safe_relative,
)

# Subcommand functions (backward compatibility)
from .analysis import _analyze_ninja_log, _cmd_build_time, _cmd_size, _cmd_size_diff
from .baseline import _cmd_bench, _cmd_check_budget, _cmd_track, _compare_benchmarks
from .external import _cmd_godbolt, _cmd_graph
from .profiling import _cmd_concurrency, _cmd_stat, _cmd_valgrind, _cmd_vec
from .tuning import _cmd_hw_recommend, _cmd_promote, _impl_cmd_autotune
