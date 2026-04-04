#!/usr/bin/env python3
"""Deterministic scenario for the generator: create a project, inspect, small edit, and re-generate.

This script is intentionally conservative: it focuses on generation + config checks
and runs a cmake configure step (if available) instead of attempting a full build.

Run from repository root:
    python3 scripts/stress/scenarios/generator_deterministic.py
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]

# Import harness by path so this script can be executed from the repo root
HARNESS_PATH = REPO_ROOT / "scripts" / "stress" / "harness.py"
spec = importlib.util.spec_from_file_location("ccpt_harness", str(HARNESS_PATH))
hmod = importlib.util.module_from_spec(spec)
import sys as _sys
_sys.modules[spec.name] = hmod
spec.loader.exec_module(hmod)
Harness = hmod.Harness


def main():
    h = Harness()
    results = []

    proj1 = h.root / "proj1"
    # Step 1: create a new project non-interactively
    cmd_new = [str(h.tool_script), "new", "MyProject", "--non-interactive", "--target-dir", str(proj1)]
    results.append(h.run_cmd(cmd_new, cwd=REPO_ROOT, step_name="new_proj1", use_python=True))

    # Basic checks
    ok_proj = proj1.exists()
    results[-1]["project_exists"] = ok_proj

    cmake_p = proj1 / "CMakeLists.txt"
    results.append({
        "check_cmake_exists": cmake_p.exists(),
        "path": str(cmake_p),
    })

    # Step 2: list generator components and profiles
    # `generate` exposes `--list` (dest=list_components)
    results.append(h.run_cmd([str(h.tool_script), "generate", "--list"], cwd=REPO_ROOT, step_name="list_components"))
    results.append(h.run_cmd([str(h.tool_script), "generate", "--list-profiles"], cwd=REPO_ROOT, step_name="list_profiles"))

    # Step 3: cmake configure (if cmake exists)
    if shutil.which("cmake"):
        cfg_cmd = ["cmake", "-S", str(proj1), "-B", str(proj1 / "build"), "-DCMAKE_BUILD_TYPE=Debug"]
        results.append(h.run_cmd(cfg_cmd, cwd=proj1, step_name="cmake_config", use_python=False))
    else:
        results.append({"skipped_cmake": True, "reason": "cmake not found in PATH"})

    # Step 4: simulate small user edit
    target_edit = proj1 / "README.md"
    if not target_edit.exists():
        # fall back to CMakeLists.txt
        target_edit = proj1 / "CMakeLists.txt"

    try:
        with open(target_edit, "a", encoding="utf-8") as f:
            f.write("\n# Stress-test edit: adding a small comment\n")
        results.append({"edited": str(target_edit)})
    except Exception as e:
        results.append({"edit_failed": str(e)})

    # Step 5: run generate --merge against target (conservative)
    results.append(h.run_cmd([str(h.tool_script), "generate", "--target-dir", str(proj1), "--merge"], cwd=REPO_ROOT, step_name="generate_merge"))

    # Step 6: run generate --force to overwrite
    results.append(h.run_cmd([str(h.tool_script), "generate", "--target-dir", str(proj1), "--force"], cwd=REPO_ROOT, step_name="generate_force"))

    # Step 7: dry-run explain JSON
    results.append(h.run_cmd([str(h.tool_script), "generate", "--target-dir", str(proj1), "--dry-run", "--explain", "--json"], cwd=REPO_ROOT, step_name="generate_explain_json"))

    # Write summary via harness helper
    h.write_summary()

    # Print concise summary to stdout so caller can capture it
    summary = h.summary()
    print(json.dumps({
        "scenario_root": str(h.root),
        "total_steps": summary["total_steps"],
        "failures": summary["failures"],
    }, indent=2))

    if summary["failures"]:
        print("Failures detected. See summary and logs under:", str(h.root))
    else:
        print("Scenario completed without failures. Logs at:", str(h.root))


if __name__ == "__main__":
    main()
