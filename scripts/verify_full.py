#!/usr/bin/env python3
"""Full verification script: runs build/test/extension and lib flows.

Stops on first failure and writes logs to build_logs/verify.log
"""
from __future__ import annotations

import subprocess
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "build_logs" / "verify.log"
LOG.parent.mkdir(parents=True, exist_ok=True)

def run(cmd, cwd=ROOT):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write("\n$ " + " ".join(cmd) + "\n")
        try:
            res = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            f.write(res.stdout)
            if res.returncode != 0:
                f.write(f"\n[ERROR] Command failed with exit {res.returncode}\n")
                return res.returncode
            return 0
        except Exception as e:
            f.write(f"\n[EXCEPTION] {e}\n")
            return 2

def main():
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
