#!/usr/bin/env python3
"""
plugins/hooks.py — Git pre-commit hook installer plugin.

Usage: tool hooks [--install]
"""
from __future__ import annotations

import argparse
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from core.utils.common import Logger, PROJECT_ROOT

PLUGIN_META = {
    "name": "hooks",
    "description": "Install git pre-commit hooks for the project.",
}


def find_hook_sources(root: Path) -> list[Path]:
    candidates = [
        root / "hooks",
        root / ".githooks",
        root / "scripts" / "hooks",
        root / "scripts" / "plugins" / "hooks",
    ]
    out: list[Path] = []
    for c in candidates:
        if c.exists() and c.is_dir():
            for p in sorted(c.iterdir()):
                if p.is_file():
                    out.append(p)
    return out


def main(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(prog="tool hooks")
    parser.add_argument(
        "--install",
        nargs="*",
        metavar="HOOK",
        help="Install named hooks; provide no names to install all",
    )
    parser.add_argument(
        "--uninstall",
        nargs="*",
        metavar="HOOK",
        help="Uninstall named hooks; provide no names to uninstall all",
    )
    parser.add_argument(
        "--run",
        nargs="*",
        metavar="HOOK",
        help="Run named hooks for testing; provide no names to run all",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Operate on all found hooks (same as no names)",
    )
    parser.add_argument(
        "--help-long",
        action="store_true",
        help="Show extended help, examples and creative suggestions (non-standard)",
    )
    args = parser.parse_args(argv)

    if getattr(args, "help_long", False):
        help_text = """
Extended help — hooks installer

Description:
  `python3 scripts/tool.py hooks` discovers hook templates in these locations:
    - hooks/
    - .githooks/
    - scripts/hooks/
    - scripts/plugins/hooks/

  Use the flags below to install, uninstall or run templates. You may provide
  hook filenames or stems to operate on specific hooks; if no names are given
  the command operates on all discovered hooks.

Examples:
  # Install a specific hook (by filename or stem):
  python3 scripts/tool.py hooks --install cmake_format_stage

  # Install all discovered hooks:
  python3 scripts/tool.py hooks --install
  python3 scripts/tool.py hooks --install --all

  # Uninstall a single hook:
  python3 scripts/tool.py hooks --uninstall cmake_format_stage

  # Run (test) a single hook without installing:
  python3 scripts/tool.py hooks --run cmake_format_stage

  # Run all hooks (test):
  python3 scripts/tool.py hooks --run --all

Notes and tips:
  - If you use `pre-commit` framework in the project, prefer adding a local
    `repo: local` entry in `.pre-commit-config.yaml` that points to the
    Python hook (e.g. scripts/plugins/hooks/cmake_format_stage.py). This avoids
    shell portability issues and works cross-platform.
  - `--run` is intended for testing templates locally prior to installation.

Creative ideas (non-implemented suggestions):
  - Add an interactive TUI (`scripts/tui.py hooks`) to enable per-developer
    enabling/disabling of hooks and previewing their effects.
  - Introduce a `hooks sync` command to pull/refresh hook templates from a
    central repository, with versioning metadata in a `hooks.json` registry.
  - Add a GitHub Action that runs `python3 scripts/tool.py hooks --run --all`
    in CI to verify hook templates don't fail in a clean environment.
  - Provide an opt-in `hooks apply --auto` that runs and auto-commits safe
    formatting fixes (use with caution — may add unexpected changes).

"""
        print(help_text)
        return

    sources = find_hook_sources(PROJECT_ROOT)
    if not sources:
        Logger.info(
            "No hook templates found in hooks/, .githooks/, scripts/hooks/ or scripts/plugins/hooks/"
        )
        return

    # Determine which action was requested. Only one action is allowed at a time.
    actions: list[str] = []
    if args.install is not None:
        actions.append("install")
    if args.uninstall is not None:
        actions.append("uninstall")
    if args.run is not None:
        actions.append("run")

    if len(actions) == 0:
        Logger.info("Found hook templates:")
        for s in sources:
            print(f" - {s.relative_to(PROJECT_ROOT)}")
        print("\nRun with --install/--uninstall/--run to operate on hooks (optionally provide names)")
        return

    if len(actions) > 1:
        Logger.error("Please provide exactly one of --install, --uninstall or --run at a time.")
        return

    action = actions[0]

    # Get the requested names for the action. None => option not provided, but we already
    # know it was provided because it's in actions; empty list => provided but no names => all.
    requested = getattr(args, action)

    # If --all specified, treat as asking for all hooks
    if args.all:
        requested = []

    # Validate empty name entries
    if requested is not None and any((n is None) or (not str(n).strip()) for n in requested):
        Logger.error("Empty hook name provided; please give a valid hook filename or stem.")
        return

    def matches_name(path: Path, name: str) -> bool:
        return path.name == name or path.stem == name

    if requested is None or len(requested) == 0:
        selected = list(sources)
    else:
        selected = [s for s in sources if any(matches_name(s, n) for n in requested)]
        if not selected:
            Logger.error(f"No hook templates matched the requested names: {requested}")
            return

    if action == "run":
        Logger.info("Running selected hook templates for test...")
        any_failed = False
        for src in selected:
            rel = src.relative_to(PROJECT_ROOT)
            Logger.info(f"Running template: {rel}")
            try:
                if src.suffix == ".py":
                    cmd = [sys.executable, str(src)]
                    res = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
                else:
                    # Try running via shell; this is meant for simple hook templates.
                    res = subprocess.run(str(src), cwd=str(PROJECT_ROOT), shell=True)
                if res.returncode == 0:
                    Logger.success(f"Ran hook: {rel}")
                else:
                    Logger.error(f"Hook {rel} exited with code {res.returncode}")
                    any_failed = True
            except Exception as e:
                Logger.error(f"Failed to run {rel}: {e}")
                any_failed = True
        if any_failed:
            return
        return

    # Proceed to install/uninstall selected hooks

    git_dir = PROJECT_ROOT / ".git"
    if not git_dir.exists():
        Logger.error("No .git directory found; hooks can only be installed/removed in a git repository.")
        return

    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)

    if args.uninstall:
        for src in selected:
            dest = hooks_dir / src.name
            if dest.exists():
                try:
                    dest.unlink()
                    Logger.success(f"Removed installed hook: {src.name}")
                except Exception as e:
                    Logger.error(f"Failed to remove {dest}: {e}")
            else:
                Logger.info(f"No installed hook found for: {src.name}")
        return

    # Install
    for src in selected:
        dest = hooks_dir / src.name
        shutil.copy2(src, dest)
        # Make executable
        try:
            dest.chmod(dest.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        except Exception:
            pass
        Logger.success(f"Installed hook: {src.name}")
