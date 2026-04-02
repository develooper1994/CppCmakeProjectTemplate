#!/usr/bin/env python3
"""Full verification plugin: runs build/test/extension and lib flows.

Stops on first failure and writes logs to build_logs/verify.log
"""
from __future__ import annotations

from pathlib import Path
import sys
import argparse

PLUGIN_META = {
    "name": "verify",
    "description": "Run full verification: build, test, extension, and library flows.",
    "args": [
        {"name": "install", "help": "Install dev dependencies before running", "type": "flag"},
        {"name": "recreate", "help": "Recreate venv when used with --install", "type": "flag"},
    ],
}

# Ensure scripts/ is on sys.path so `core.*` imports work when the module
# is imported as a package or executed directly.
_SCRIPTS = Path(__file__).resolve().parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
from core.utils.common import run_capture, install_dev_env

ROOT = Path(__file__).resolve().parent.parent.parent
LOG = ROOT / "build_logs" / "verify.log"
LOG.parent.mkdir(parents=True, exist_ok=True)


def run(cmd, cwd=ROOT):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write("\n$ " + " ".join(cmd) + "\n")
        try:
            out, rc = run_capture(cmd, cwd=cwd, strip_ansi=False)
            # Preserve a trailing newline similar to subprocess output
            try:
                f.write(out + "\n")
            except Exception:
                f.write(str(out) + "\n")
            if rc != 0:
                f.write(f"\n[ERROR] Command failed with exit {rc}\n")
                return rc
            return 0
        except Exception as e:
            f.write(f"\n[EXCEPTION] {e}\n")
            return 2

def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(prog="verify_full")
    parser.add_argument("--install", action="store_true", help="Install dev dependencies into .venv before running")
    parser.add_argument("--recreate", action="store_true", help="Recreate the venv when used with --install")
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    if args.install:
        install_dev_env(recreate=bool(args.recreate))

    steps = [
        [sys.executable, "scripts/tool.py", "build", "check"],
        [sys.executable, "scripts/tool.py", "build", "extension"],
        [sys.executable, "scripts/tool.py", "lib", "add", "demo_lib", "--template", "singleton", "--dry-run"],
        [sys.executable, "scripts/tool.py", "lib", "add", "demo_lib", "--template", "singleton"],
        [sys.executable, "scripts/tool.py", "lib", "export", "demo_lib", "--dry-run"],
        [sys.executable, "scripts/tool.py", "lib", "export", "demo_lib"],
        [sys.executable, "scripts/tool.py", "lib", "remove", "demo_lib", "--delete"],
        [sys.executable, "scripts/tool.py", "sol", "doctor"],
        [sys.executable, "scripts/tool.py", "session", "save", "--default-cmd", "build check"],
        [sys.executable, "scripts/tool.py", "session", "load", "--print"],
    ]

    for cmd in steps:
        rc = run(cmd)
        if rc != 0:
            print(f"Step failed: {' '.join(cmd)} (rc={rc}). See {LOG}")
            sys.exit(rc)

    print("All verification steps completed successfully. See build_logs/verify.log for details.")

if __name__ == '__main__':
    main()
