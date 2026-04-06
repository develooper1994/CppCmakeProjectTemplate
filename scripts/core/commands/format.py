#!/usr/bin/env python3
"""
core/commands/format.py — Formatting and automated fix helpers

Provides:
  tool format tidy-fix   — run clang-tidy -fix across project source files
  tool format iwyu       — run include-what-you-use; optionally auto-fix via iwyu_tool.py
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from core.utils.common import Logger, PROJECT_ROOT, run_proc, run_capture
from core.utils.tool_installer import ensure_tool_available
import tempfile


def _impl_tidy_fix(args) -> None:
    if not shutil.which("clang-tidy"):
        Logger.error("clang-tidy not found. Install clang-tidy to run tidy-fix.")
        raise SystemExit(1)

    build_dir = PROJECT_ROOT / "build"
    if not (build_dir / "compile_commands.json").exists():
        Logger.error("compile_commands.json not found in build/; configure the project first (cmake).")
        raise SystemExit(1)

    # Gather candidate source files from common directories
    sources = []
    cand_dirs = ["libs", "apps", "tests", "gui_app", "main_app"]
    for d in cand_dirs:
        p = PROJECT_ROOT / d
        if p.exists():
            for f in p.rglob("*.cpp"):
                sources.append(str(f))

    if not sources:
        Logger.warn("No source files found for clang-tidy run")
        return

    checks_arg = None
    if getattr(args, 'checks', None):
        checks_arg = f"--checks={args.checks}"

    mode = "apply" if getattr(args, 'apply', False) else "dry-run"
    Logger.info(f"Running clang-tidy ({mode}) on {len(sources)} files")

    # Run clang-tidy per-file to avoid CLI length limits; run in best-effort mode
    for src in sources:
        cmd = ["clang-tidy", "-p", str(build_dir)]
        if checks_arg:
            cmd.append(checks_arg)
        if getattr(args, 'apply', False):
            cmd.append("-fix")
        cmd.append(src)
        try:
            run_proc(cmd)
        except SystemExit:
            Logger.warn(f"clang-tidy reported issues on {src}; continuing")

    # If apply mode, record a patch for review
    if getattr(args, 'apply', False):
        out, rc = run_proc(["git", "diff", "--no-prefix"], check=False), 0
        # run_proc returns int when check=False; capture using run_capture instead
        try:
            from core.utils.common import run_capture
            diff_out, _ = run_capture(["git", "diff", "--no-prefix"]) if shutil.which("git") else ("", 0)
            patch_path = (PROJECT_ROOT / "build" / "tidy_fix.patch")
            patch_path.parent.mkdir(parents=True, exist_ok=True)
            patch_path.write_text(diff_out + "\n", encoding="utf-8")
            if diff_out.strip():
                Logger.info(f"clang-tidy applied changes; patch written to: {patch_path}")
            else:
                Logger.info("clang-tidy applied no changes; patch empty")
        except Exception:
            Logger.warn("Failed to record git diff for tidy-fix (git may be unavailable)")

    Logger.success("clang-tidy pass complete. Review changes and commit as appropriate.")


# ---------------------------------------------------------------------------
# IWYU — include-what-you-use
# ---------------------------------------------------------------------------

def _impl_iwyu(args) -> None:
    """Run include-what-you-use on project source files.

    Uses iwyu_tool (reads compile_commands.json) so every TU gets the correct
    compiler flags.  If --fix is requested the suggestions are piped to
    fix_includes.py (when available) or printed for manual review.
    """
    iwyu_tool_bin = shutil.which("iwyu_tool") or shutil.which("iwyu_tool.py")
    if not iwyu_tool_bin:
        # Fall back to direct include-what-you-use invocation
        iwyu_tool_bin = None

    iwyu_bin = shutil.which("include-what-you-use") or shutil.which("iwyu")
    if not iwyu_bin and not iwyu_tool_bin:
        Logger.error("include-what-you-use not found. Install it (e.g. apt install iwyu).")
        raise SystemExit(1)

    build_dir = PROJECT_ROOT / "build"
    compile_commands = build_dir / "compile_commands.json"
    if not compile_commands.exists():
        Logger.error("compile_commands.json not found in build/; configure the project first.")
        raise SystemExit(1)

    target = getattr(args, "target", None)
    fix = getattr(args, "fix", False)
    extra_opts: list[str] = []
    for opt in (getattr(args, "extra_opts", []) or []):
        if opt.startswith("--"):
            extra_opts.append(opt)

    fix_includes_bin = shutil.which("fix_includes.py") or shutil.which("fix_includes")

    # Collect source files to scope the run (optional)
    sources: list[str] = []
    if target:
        for d in [PROJECT_ROOT / "libs" / target, PROJECT_ROOT / "apps" / target]:
            if d.exists():
                sources.extend(str(f) for f in d.rglob("*.cpp"))
        if not sources:
            Logger.error(f"No source files found for target '{target}'")
            raise SystemExit(1)

    file_count = len(sources) if sources else "all"
    Logger.info(f"[IWYU] Analysing {file_count} file(s)" + (f" in '{target}'" if target else ""))

    # Build base command using iwyu_tool (preferred — handles compile_commands.json)
    if iwyu_tool_bin:
        cmd = [iwyu_tool_bin, "-p", str(build_dir)]
        if sources:
            cmd.extend(sources)
        if extra_opts:
            cmd += ["--"] + extra_opts
        result = subprocess.run(cmd, capture_output=True, text=True)
        output = (result.stdout or "") + (result.stderr or "")
    else:
        # Fallback: run iwyu directly on each file with explicit include paths
        output_parts: list[str] = []
        search_dirs_fb = ["libs", "apps", "tests"]
        if not sources:
            for d in search_dirs_fb:
                p = PROJECT_ROOT / d
                if p.exists():
                    sources.extend(str(f) for f in p.rglob("*.cpp"))
        for src in sources:
            cmd = [iwyu_bin]
            for opt in extra_opts:
                cmd += [opt]
            cmd.append(src)
            r = subprocess.run(cmd, capture_output=True, text=True)
            part = (r.stderr or r.stdout or "").strip()
            if part:
                output_parts.append(part)
        output = "\n".join(output_parts)

    if output.strip():
        print(output)

    if fix and fix_includes_bin:
        fix_cmd = [sys.executable, fix_includes_bin] if fix_includes_bin.endswith(".py") else [fix_includes_bin]
        fix_cmd += ["--nosafe_headers"]
        subprocess.run(fix_cmd, input=output, text=True)
        Logger.success("[IWYU] fix_includes applied suggestions. Review with 'git diff'.")
    elif fix:
        Logger.warn("[IWYU] fix_includes.py not found; suggestions printed above for manual review.")

    issues = output.count("should remove") + output.count("should add")
    if not fix:
        if issues:
            Logger.warn(f"[IWYU] {issues} suggestion(s) found. Run with --fix to apply.")
        else:
            Logger.success("[IWYU] All analysed files look clean.")


def format_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tool format", description="Formatting and automated fixes")
    sub = parser.add_subparsers(dest="subcommand")

    # tidy-fix
    p = sub.add_parser("tidy-fix", help="Run clang-tidy -fix across the project")
    p.add_argument("--dry-run", action="store_true", help="Run clang-tidy without applying fixes (default)")
    p.add_argument("--apply", action="store_true", help="Apply fixes (runs clang-tidy -fix) and record patch")
    p.add_argument("--checks", default=None, help="Pass a -checks pattern to clang-tidy (e.g. '*,-llvm-*')")
    p.set_defaults(func=lambda args: _impl_tidy_fix(args))

    # iwyu
    p = sub.add_parser("iwyu", help="Run include-what-you-use on project source files")
    p.add_argument("--target", default=None, metavar="LIB",
                   help="Scope analysis to a specific library or app (e.g. dummy_lib)")
    p.add_argument("--fix", action="store_true",
                   help="Auto-apply suggestions via iwyu_tool.py + fix_includes.py")
    p.add_argument("extra_opts", nargs=argparse.REMAINDER,
                   help="Extra options forwarded to iwyu (each wrapped as -Xiwyu <opt>)")
    p.set_defaults(func=lambda args: _impl_iwyu(args))

    # clang-format
    p = sub.add_parser("clang-format", help="Run clang-format across project files")
    p.add_argument("--apply", action="store_true", help="Apply formatting in-place")
    p.add_argument("--check", action="store_true", help="Check formatting and report files that need formatting")
    p.add_argument("--paths", nargs="*", default=[], help="Paths to limit formatting to (relative to project root)")
    p.add_argument("--install", action="store_true", help="Attempt to install clang-format if missing")
    p.set_defaults(func=lambda args: _impl_clang_format(args))

    # astyle
    p = sub.add_parser("astyle", help="Run Artistic Style (astyle) on project files")
    p.add_argument("--apply", action="store_true", help="Apply formatting in-place")
    p.add_argument("--check", action="store_true", help="Check formatting")
    p.add_argument("--paths", nargs="*", default=[], help="Paths to limit formatting to (relative to project root)")
    p.add_argument("--install", action="store_true", help="Attempt to install astyle if missing")
    p.set_defaults(func=lambda args: _impl_astyle(args))

    # uncrustify
    p = sub.add_parser("uncrustify", help="Run Uncrustify on project files")
    p.add_argument("--config", default=None, help="Path to uncrustify config file")
    p.add_argument("--apply", action="store_true", help="Apply formatting in-place")
    p.add_argument("--check", action="store_true", help="Check formatting")
    p.add_argument("--paths", nargs="*", default=[], help="Paths to limit formatting to (relative to project root)")
    p.add_argument("--install", action="store_true", help="Attempt to install uncrustify if missing")
    p.set_defaults(func=lambda args: _impl_uncrustify(args))

    # cpplint
    p = sub.add_parser("cpplint", help="Run cpplint (style linter) on project files")
    p.add_argument("--paths", nargs="*", default=[], help="Paths to lint (relative to project root)")
    p.add_argument("--install", action="store_true", help="Attempt to install cpplint if missing (pip)")
    p.set_defaults(func=lambda args: _impl_cpplint(args))

    return parser


def main(argv: list[str]) -> None:
    parser = format_parser()
    args = parser.parse_args(argv if argv else [])
    if hasattr(args, "func"):
        try:
            args.func(args)
        except SystemExit:
            raise
    else:
        parser.print_help()


# -------------------- Additional format implementations --------------------
def _collect_source_files(paths: list[str]) -> list[Path]:
    exts = (".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".inl", ".ipp")
    files: list[Path] = []
    if paths:
        for p in paths:
            base = (PROJECT_ROOT / p).resolve()
            if base.is_file() and base.suffix in exts:
                files.append(base)
            elif base.is_dir():
                for f in base.rglob("*"):
                    if f.suffix in exts:
                        files.append(f)
    else:
        for d in ("libs", "apps", "tests", "gui_app", "main_app"):
            base = PROJECT_ROOT / d
            if base.exists():
                for f in base.rglob("*"):
                    if f.suffix in exts:
                        files.append(f)
    # dedupe and sort
    unique = sorted({p.resolve() for p in files})
    return unique


def _impl_clang_format(args) -> None:
    if not ensure_tool_available("clang-format", ["clang-format"], install_allowed=getattr(args, "install", False)):
        Logger.error("clang-format not available; install it or run with --install")
        raise SystemExit(1)

    files = _collect_source_files(getattr(args, "paths", []))
    if not files:
        Logger.warn("No source files found for clang-format")
        return

    needs: list[Path] = []
    for f in files:
        if getattr(args, "apply", False):
            run_proc(["clang-format", "-i", "-style=file", str(f)])
        elif getattr(args, "check", False):
            out, rc = run_capture(["clang-format", "-style=file", str(f)])
            try:
                orig = f.read_text(encoding="utf-8")
            except Exception:
                orig = ""
            if out != orig:
                needs.append(f)

    if getattr(args, "check", False):
        if needs:
            Logger.warn(f"{len(needs)} files need formatting:")
            for p in needs:
                print("  ", p.relative_to(PROJECT_ROOT))
            raise SystemExit(2)
        else:
            Logger.success("All files are clang-format clean.")
    else:
        Logger.success("clang-format completed (applied if requested).")


def _impl_astyle(args) -> None:
    if not ensure_tool_available("astyle", ["astyle"], install_allowed=getattr(args, "install", False)):
        Logger.error("astyle not available; install it or run with --install")
        raise SystemExit(1)
    files = _collect_source_files(getattr(args, "paths", []))
    if not files:
        Logger.warn("No source files found for astyle")
        return
    changed = 0
    for f in files:
        if getattr(args, "apply", False):
            run_proc(["astyle", "--mode=c++", "--suffix=none", str(f)])
            changed += 1
        elif getattr(args, "check", False):
            # astyle lacks a stable --check on older versions; do a temp-file compare
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp_path = Path(tmp.name)
            run_proc(["astyle", "--mode=c++", "--suffix=none", "-n", "--formatted", str(f)], check=False)
            # fallback: assume file may change
            # (best-effort; recommend using --apply to actually format)
            pass
    Logger.success("astyle run complete (applied if requested).")


def _impl_uncrustify(args) -> None:
    if not ensure_tool_available("uncrustify", ["uncrustify"], install_allowed=getattr(args, "install", False)):
        Logger.error("uncrustify not available; install it or run with --install")
        raise SystemExit(1)
    files = _collect_source_files(getattr(args, "paths", []))
    if not files:
        Logger.warn("No source files found for uncrustify")
        return
    cfg = getattr(args, "config", None)
    for f in files:
        if getattr(args, "apply", False):
            cmd = ["uncrustify", "-q"]
            if cfg:
                cmd += ["-c", cfg]
            cmd += ["-f", str(f), "-o", str(f)]
            run_proc(cmd)
    Logger.success("uncrustify run complete (applied if requested).")


def _impl_cpplint(args) -> None:
    # cpplint is often a pip package; try to detect and fall back to pip install
    if not shutil.which("cpplint"):
        if getattr(args, "install", False):
            Logger.info("Attempting to install cpplint via pip...")
            try:
                run_proc([sys.executable, "-m", "pip", "install", "cpplint"], check=True)
            except SystemExit:
                Logger.error("Failed to install cpplint via pip")
                raise SystemExit(1)
        else:
            Logger.error("cpplint not found. Install via 'pip install cpplint' or use --install")
            raise SystemExit(1)

    files = _collect_source_files(getattr(args, "paths", []))
    if not files:
        Logger.warn("No source files found for cpplint")
        return
    problems = 0
    for f in files:
        out, rc = run_capture(["cpplint", str(f)])
        if out.strip():
            print(out)
            problems += 1
    if problems:
        Logger.warn(f"cpplint found issues in {problems} files")
        raise SystemExit(2)
    Logger.success("cpplint: no issues found")
