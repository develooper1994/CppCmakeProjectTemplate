#!/usr/bin/env python3
"""Generation idempotency check.

Generate the project into a temp target, record file hashes, generate again
into the same target and compare. Reports added/removed/modified files.

Writes outputs via the Harness run logs and prints a JSON summary.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
from pathlib import Path
from typing import Dict

REPO_ROOT = Path(__file__).resolve().parents[3]
HARNESS_PATH = REPO_ROOT / "scripts" / "stress" / "harness.py"

spec = importlib.util.spec_from_file_location("ccpt_harness", str(HARNESS_PATH))
hmod = importlib.util.module_from_spec(spec)
import sys as _sys
_sys.modules[spec.name] = hmod
spec.loader.exec_module(hmod)
Harness = hmod.Harness


def sha256_of_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        while True:
            chunk = fh.read(8192)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def collect_hashes(root: Path) -> Dict[str, str]:
    data: Dict[str, str] = {}
    for p in sorted(root.rglob("*")):
        if p.is_file():
            # skip build and generated runtime artifacts
            parts = set(p.parts)
            if 'build' in parts or '.git' in parts:
                continue
            rel = str(p.relative_to(root))
            data[rel] = sha256_of_file(p)
    return data


def main() -> None:
    base_tmp = os.environ.get("BASE_TMP")
    h = Harness(base_tmp=base_tmp) if base_tmp else Harness()
    tool = str(h.tool_script)

    target = Path(h.artifacts_dir) / "idempotency_project"
    if target.exists():
        shutil.rmtree(target)

    cmd = [tool, 'generate', '--profile', 'minimal', '--target-dir', str(target)]
    print('Running first generate...')
    r1 = h.run_cmd(cmd, cwd=REPO_ROOT, step_name='generate_first')

    before = collect_hashes(target)

    print('Running second generate (idempotency) ...')
    r2 = h.run_cmd(cmd, cwd=REPO_ROOT, step_name='generate_second')

    after = collect_hashes(target)

    added = sorted([p for p in after.keys() if p not in before])
    removed = sorted([p for p in before.keys() if p not in after])
    modified = sorted([p for p in before.keys() if p in after and before[p] != after[p]])

    summary = {
        'root': str(h.root),
        'target': str(target),
        'first_rc': r1['returncode'],
        'second_rc': r2['returncode'],
        'added': added,
        'removed': removed,
        'modified': modified,
    }

    print(json.dumps(summary, indent=2))
    h.write_summary()

    # Cleanup generated target as requested (keep run logs)
    try:
        if target.exists():
            shutil.rmtree(target)
    except Exception:
        pass


if __name__ == '__main__':
    main()
