"""Analyzer plugin: clazy

Simple plugin wrapper for `clazy`. Implements a minimal `run()` entrypoint
expected by `tool analyze`.
"""
from __future__ import annotations

from core.utils.common import Logger, PROJECT_ROOT, run_capture
from core.utils.tool_installer import ensure_tool_available


def run(install_allowed: bool = False) -> int:
    candidates = ["clazy", "clazy-standalone"]
    ok = ensure_tool_available("clazy", candidates, install_allowed=install_allowed)
    if not ok:
        Logger.error("clazy not available")
        return 1
    # Minimal run: output version and write to log
    cmd = ["clazy", "--version"]
    out, rc = run_capture(cmd)
    log = PROJECT_ROOT / "build" / "build_logs" / "analyze_clazy.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(out + "\n", encoding='utf-8')
    if rc == 0:
        Logger.success("clazy: version check OK")
    else:
        Logger.warn("clazy: version check returned non-zero")
    return rc
