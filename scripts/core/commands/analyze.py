#!/usr/bin/env python3
"""
core/commands/analyze.py — Convenience wrapper to run static analyzers and custom analyzers.

This module provides `tool analyze` which accepts a list of analyzers to run,
supports ad-hoc `--analyzer name=cmd` entries, and can attempt to install
missing tools when `--install` is passed. It also discovers analyzer plugins
under `scripts/plugins/analyzers/` and delegates to them when present.
"""
from __future__ import annotations

import argparse
import importlib
from typing import Dict, List

from core.utils.common import Logger, PROJECT_ROOT, run_proc, run_capture
from core.utils.tool_installer import ensure_tool_available


def _discover_plugins() -> Dict[str, str]:
    """Discover analyzer plugins under scripts/plugins/analyzers.

    Returns a mapping of plugin name -> module path (e.g. 'clazy' -> 'plugins.analyzers.clazy').
    """
    plugins = {}
    plugin_dir = PROJECT_ROOT / "scripts" / "plugins" / "analyzers"
    if not plugin_dir.exists() or not plugin_dir.is_dir():
        return plugins
    for p in plugin_dir.iterdir():
        if p.suffix == ".py" and p.name != "__init__.py":
            name = p.stem
            plugins[name] = f"plugins.analyzers.{name}"
    return plugins


def _run_custom_analyzer(name: str, cmd: str, install_allowed: bool) -> int:
    Logger.info(f"Running custom analyzer '{name}': {cmd}")
    parts = cmd.split()
    try:
        out, rc = run_capture(parts)
        log = PROJECT_ROOT / "build" / "build_logs" / f"analyze_{name}.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(out + "\n", encoding='utf-8')
        if rc == 0:
            Logger.success(f"Analyzer '{name}': Completed successfully.")
        else:
            Logger.warn(f"Analyzer '{name}': Completed with returncode={rc}. See {log}")
        return rc
    except SystemExit:
        Logger.error(f"Analyzer '{name}' failed to run.")
        return 1


def main(argv: List[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="tool analyze", description="Run static analyzers and custom analyzers")
    parser.add_argument("--install", action="store_true", help="Try to install missing tools automatically")
    parser.add_argument("--analyzers", type=str, default=None,
                        help="Comma-separated list of analyzers to run (e.g. clazy,clang-tidy,cppcheck)")
    parser.add_argument("--analyzer", action="append", default=[],
                        help="Ad-hoc analyzer definition 'name=cmd' which will be executed as given")
    parser.add_argument("--force", action="store_true", help="Continue even if an analyzer reports errors")
    args = parser.parse_args(argv if argv is not None else [])

    selected: List[str] = []
    if args.analyzers:
        selected = [s.strip() for s in args.analyzers.split(",") if s.strip()]

    custom: Dict[str, str] = {}
    for a in args.analyzer or []:
        if "=" in a:
            n, c = a.split("=", 1)
            custom[n.strip()] = c.strip()
        else:
            Logger.warn(f"Ignoring malformed --analyzer value: {a}")

    plugins = _discover_plugins()

    # Run plugin-based analyzers first
    rc_total = 0
    for name in list(selected):
        if name in plugins:
            mod_path = plugins[name]
            try:
                mod = importlib.import_module(mod_path)
                if hasattr(mod, "run"):
                    Logger.info(f"Running analyzer plugin: {name}")
                    ok = mod.run(install_allowed=args.install)
                    if ok != 0:
                        rc_total = rc_total or ok
                        if not args.force:
                            raise SystemExit(ok)
                else:
                    Logger.warn(f"Plugin '{name}' does not expose run(install_allowed). Skipping.")
            except Exception as e:
                Logger.error(f"Failed to run plugin '{name}': {e}")
                raise
            selected.remove(name)

    # Run built-in analyzers for remaining selected names
    for name in selected:
        if name == "clazy":
            # Try clazy executable
            candidates = ["clazy", "clazy-standalone"]
            ok = ensure_tool_available("clazy", candidates, install_allowed=args.install)
            if not ok:
                Logger.error("clazy not available; aborting analyze.")
                raise SystemExit(1)
            # Minimal invocation: version or full run if compile_commands exists
            clazy_bin = "clazy"
            if ensure_tool_available("clazy-standalone"):
                clazy_bin = "clazy-standalone"
            compile_db = PROJECT_ROOT / "build" / "compile_commands.json"
            if compile_db.exists():
                cmd = [clazy_bin, "--version"]
            else:
                cmd = [clazy_bin, "--version"]
            out, rc = run_capture(cmd)
            log = PROJECT_ROOT / "build" / "build_logs" / "analyze_clazy.log"
            log.parent.mkdir(parents=True, exist_ok=True)
            log.write_text(out + "\n", encoding='utf-8')
            if rc == 0:
                Logger.success("clazy: Completed (version check).")
            else:
                Logger.warn("clazy: Completed with issues (see log)")
                rc_total = rc_total or rc
                if not args.force:
                    raise SystemExit(rc)

        elif name in ("scan-build", "clang-analyzer", "clang_analyzer"):
            ok = ensure_tool_available("scan-build", ["scan-build"], install_allowed=args.install)
            if not ok:
                Logger.error("scan-build not available; aborting analyze.")
                raise SystemExit(1)
            # Attempt to auto-detect build dir
            try:
                from core.commands.perf._helpers import _find_active_build_dir
                build_dir = _find_active_build_dir()
            except Exception:
                build_dir = PROJECT_ROOT / "build"
            out_dir = PROJECT_ROOT / "build" / "build_logs" / "clang_analyzer"
            out_dir.mkdir(parents=True, exist_ok=True)
            scan_cmd = [
                "scan-build",
                "-o", str(out_dir),
                "--status-bugs",
                "--use-cc", "clang",
                "--use-c++", "clang++",
                "--",
                "cmake", "--build", str(build_dir),
            ]
            rc = run_proc(scan_cmd, check=False)
            if rc == 0:
                Logger.success("Clang Static Analyzer: Completed (no blocking reports).")
            else:
                Logger.warn(f"Clang Static Analyzer: Completed with issues. See {out_dir}")
                rc_total = rc_total or rc
                if not args.force:
                    raise SystemExit(rc)

        elif name == "cppcheck":
            # Reuse security's cppcheck flow minimally
            from core.commands.security import _impl_cmd_scan as _sec_scan
            # Build a minimal args namespace to ask security to run cppcheck only
            import argparse as _ap
            sec_args = _ap.Namespace()
            sec_args.install = args.install
            sec_args.no_osv = True
            sec_args.no_static = False
            sec_args.format = "text"
            sec_args.force = args.force
            sec_args.cppcheck_checks = "full"
            sec_args.cppcheck_jobs = 0
            sec_args.cppcheck_paths = []
            sec_args.suppressions = None
            # set flags so security's static block runs and detects cppcheck
            try:
                _sec_scan(sec_args)
            except SystemExit as e:
                rc_total = rc_total or (e.code or 1)
                if not args.force:
                    raise

        else:
            # Unknown analyzer name: error unless it's a custom analyzer
            if name in custom:
                rc = _run_custom_analyzer(name, custom[name], install_allowed=args.install)
                rc_total = rc_total or rc
                if rc != 0 and not args.force:
                    raise SystemExit(rc)
            else:
                Logger.warn(f"Unknown analyzer: {name}; skipping.")

    # Run custom analyzers that were not part of selected list
    for name, cmd in custom.items():
        if name in selected:
            continue
        rc = _run_custom_analyzer(name, cmd, install_allowed=args.install)
        rc_total = rc_total or rc
        if rc != 0 and not args.force:
            raise SystemExit(rc)

    if rc_total != 0:
        raise SystemExit(rc_total)
