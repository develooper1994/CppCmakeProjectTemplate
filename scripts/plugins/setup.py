#!/usr/bin/env python3
"""
plugins/setup.py — Dependency checker/installer plugin.

Usage: tool setup [--install] [--all]
Delegates to scripts/install_deps.py — no subprocess.
"""
from __future__ import annotations

PLUGIN_META = {
    "name": "setup",
    "description": "Check and optionally install system and Python dependencies for the project.",
    "args": [
        {"name": "install", "help": "Run installation of detected missing packages", "type": "flag", "required": False},
        {"name": "all", "help": "Install all optional dependencies as well", "type": "flag", "required": False},
    ],
}

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import install_deps as _impl  # scripts/install_deps.py


def main(argv: list[str]) -> None:
    """Support both dependency checks and Python venv bootstrap.

    - No `--env`: delegate to `install_deps.main()` (existing behavior).
    - With `--env [DIR]`: create a venv in DIR (default `.venv`).
      Use `--install-env` to also install `requirements-dev.txt` into it.
    """
    import argparse
    old_argv = sys.argv
    try:
        parser = argparse.ArgumentParser(prog="tool setup")
        parser.add_argument("--install", action="store_true", help="(informational) show installation command")
        parser.add_argument("--all", action="store_true", help="Include optional packages in the check")
        parser.add_argument("--env", nargs="?", const=".venv", default=None, help="Create Python venv (optional dir, default: .venv)")
        parser.add_argument("--install-env", action="store_true", help="Install requirements-dev.txt into created venv")
        parser.add_argument("--recreate", action="store_true", help="Recreate venv if it exists")
        args = parser.parse_args(argv)

        if args.env is not None:
            # Lazy import the venv helper to avoid adding extra deps at module import time
            try:
                import setup_python_env as _env  # scripts/setup_python_env.py
            except Exception:
                # Fallback: reuse the script's CLI parsing
                sys_argv = ["setup_python_env"]
                if args.env:
                    sys_argv += ["--env", args.env]
                if args.install_env:
                    sys_argv += ["--install"]
                if args.recreate:
                    sys_argv += ["--recreate"]
                sys.argv = sys_argv
                try:
                    # run as script
                    from setup_python_env import main as _env_main

                    _env_main()
                finally:
                    sys.argv = old_argv
                return

            py = _env.create_venv(Path(args.env), recreate=args.recreate)
            if args.install_env:
                _env.install_requirements(py, Path("requirements-dev.txt"))
            _env.print_activation(Path(args.env))
            return

        # Default: delegate to install_deps
        sys.argv = ["tool setup"] + (["--install"] if args.install else []) + (["--all"] if args.all else [])
        _impl.main()
    finally:
        sys.argv = old_argv
