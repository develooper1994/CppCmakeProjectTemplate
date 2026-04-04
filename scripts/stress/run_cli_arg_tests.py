#!/usr/bin/env python3
"""Run a small matrix of `tool.py` invocations to validate top-level vs subcommand arg routing.

Outputs are written under a timestamped directory in /tmp and a summary is printed.
"""
from __future__ import annotations

import importlib.util
import json
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HARNESS_PATH = REPO_ROOT / "scripts" / "stress" / "harness.py"
spec = importlib.util.spec_from_file_location("ccpt_harness", str(HARNESS_PATH))
hmod = importlib.util.module_from_spec(spec)
import sys as _sys
_sys.modules[spec.name] = hmod
spec.loader.exec_module(hmod)
Harness = hmod.Harness


def main():
    h = Harness()
    sp = str(h.tool_script)

    tests = [
        ("main_no_args", [sp]),
        ("main_short_help", [sp, "-h"]),
        ("main_long_help", [sp, "--help"]),
        ("main_version", [sp, "--version"]),
        ("build_subcmd_help_short", [sp, "build", "-h"]),
        ("build_subcmd_help_long", [sp, "build", "--help"]),
        ("build_prefix_help", [sp, "--build", "--help"]),
        ("build_prefix_dryrun", [sp, "--dry-run", "--build"]),
        ("build_subcmd_dryrun", [sp, "--dry-run", "build"]),
    ]

    for name, argv in tests:
        print(f"Running test: {name} -> {' '.join(argv)}")
        res = h.run_cmd(argv, cwd=REPO_ROOT, step_name=name)
        print(f"  rc={res['returncode']} log={res['stdout_path']}")

    h.write_summary()
    print("Summary written to:", h.root)
    print(json.dumps(h.summary(), indent=2))


if __name__ == "__main__":
    main()
