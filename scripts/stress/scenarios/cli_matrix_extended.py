#!/usr/bin/env python3
"""Extended CLI argument routing matrix for `tool.py`.

Runs a broader set of top-level vs subcommand invocation permutations
to validate global flag forwarding and help/version routing.

Outputs are recorded using the Harness utilities under the scenario root.
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
HARNESS_PATH = REPO_ROOT / "scripts" / "stress" / "harness.py"

spec = importlib.util.spec_from_file_location("ccpt_harness", str(HARNESS_PATH))
hmod = importlib.util.module_from_spec(spec)
import sys as _sys
_sys.modules[spec.name] = hmod
spec.loader.exec_module(hmod)
Harness = hmod.Harness


def main() -> None:
    base_tmp = os.environ.get("BASE_TMP")
    h = Harness(base_tmp=base_tmp) if base_tmp else Harness()
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
        ("double_prefix", [sp, "--dry-run", "--dry-run", "build"]),
        ("unknown_flag_before", [sp, "--unknown", "build"]),
        ("unknown_flag_after", [sp, "build", "--unknown"]),
        ("verbose_then_build", [sp, "-v", "build"]),
        ("build_then_verbose", [sp, "build", "-v"]),
        ("help_with_prefix_build", [sp, "--help", "build"]),
        ("prefix_help_moved", [sp, "--build", "--help"]),
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
