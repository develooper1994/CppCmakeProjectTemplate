#!/usr/bin/env python3
"""Argument fuzzing for generated application binaries.

Generates a minimal project, builds it, finds the primary executable,
and invokes it with randomized argument combinations to detect crashes.

Logs are stored via Harness under the scenario root.
"""
from __future__ import annotations

import importlib.util
import json
import os
import random
import shutil
import string
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
HARNESS_PATH = REPO_ROOT / "scripts" / "stress" / "harness.py"

spec = importlib.util.spec_from_file_location("ccpt_harness", str(HARNESS_PATH))
hmod = importlib.util.module_from_spec(spec)
import sys as _sys
_sys.modules[spec.name] = hmod
spec.loader.exec_module(hmod)
Harness = hmod.Harness


def find_executable_bin(target_dir: Path) -> Path | None:
    candidates = [
        target_dir / 'build',
        target_dir / 'apps',
        target_dir / 'bin',
        target_dir,
    ]
    prioritized = []
    others = []
    for base in candidates:
        if not base.exists():
            continue
        for p in base.rglob('*'):
            if not p.exists() or not p.is_file():
                continue
            # Skip common source/config extensions
            if p.suffix.lower() in {'.cpp', '.cc', '.c', '.cxx', '.h', '.hpp', '.in', '.cmake', '.py', '.md', '.txt', '.json'}:
                continue
            score = 0
            parts = [s.lower() for s in p.parts]
            if 'apps' in parts or 'app' in parts:
                score += 10
            if 'bin' in parts or 'out' in parts:
                score += 5
            if p.name.startswith('main') or p.name.endswith('_app'):
                score += 3
            try:
                if p.stat().st_mode & 0o111:
                    score += 2
            except Exception:
                pass
            try:
                with p.open('rb') as fh:
                    if fh.read(4) == b'\x7fELF':
                        score += 8
            except Exception:
                pass
            if score >= 8:
                prioritized.append((score, p))
            else:
                others.append((score, p))
    if prioritized:
        prioritized.sort(key=lambda x: (-x[0], str(x[1])))
        return prioritized[0][1]
    if others:
        others.sort(key=lambda x: (-x[0], str(x[1])))
        return others[0][1]
    return None


def rand_arg() -> str:
    # generate short random flags or values
    typ = random.choice(['flag', 'opt', 'kv', 'word'])
    if typ == 'flag':
        return random.choice(['--enable', '--disable', '--flag', '-f', '-v'])
    if typ == 'opt':
        return random.choice(['--opt', '--size', '--count', '--timeout'])
    if typ == 'kv':
        k = ''.join(random.choices(string.ascii_lowercase, k=4))
        v = str(random.randint(0, 1000))
        return f'--{k}={v}'
    return ''.join(random.choices(string.ascii_letters + string.digits, k=6))


def main() -> None:
    random.seed(42)
    base_tmp = os.environ.get("BASE_TMP")
    h = Harness(base_tmp=base_tmp) if base_tmp else Harness()
    tool = str(h.tool_script)

    target = Path(h.artifacts_dir) / 'fuzz_project'
    if target.exists():
        shutil.rmtree(target)

    # generate
    gen_cmd = [tool, 'generate', '--profile', 'minimal', '--target-dir', str(target)]
    h.run_cmd(gen_cmd, cwd=REPO_ROOT, step_name='generate_project')

    # configure & build (disable tests/docs)
    build_dir = target / 'build'
    build_dir.mkdir(parents=True, exist_ok=True)
    cfg = ['cmake', '-S', str(target), '-B', str(build_dir), '-DCMAKE_BUILD_TYPE=Release', '-DENABLE_UNIT_TESTS=OFF', '-DENABLE_GTEST=OFF', '-DENABLE_DOCS=OFF']
    h.run_cmd(cfg, cwd=target, use_python=False, step_name='cmake_configure', timeout=300)
    build = ['cmake', '--build', str(build_dir), '--config', 'Release', '--', '-j2']
    h.run_cmd(build, cwd=target, use_python=False, step_name='cmake_build', timeout=600)

    exe = find_executable_bin(target)
    if exe is None:
        print('No executable found; aborting fuzz.')
        h.write_summary()
        return

    print('Fuzzing executable:', exe)

    failures: list[dict[str, Any]] = []
    runs = 50
    for i in range(runs):
        nargs = random.randint(0, 4)
        args = [rand_arg() for _ in range(nargs)]
        argv = [str(exe)] + args
        step = f'fuzz_{i+1:03d}'
        print('Run', step, '->', ' '.join(argv))
        res = h.run_cmd(argv, cwd=target, use_python=False, step_name=step, timeout=5)
        if res['returncode'] != 0:
            failures.append({'step': step, 'cmd': res['cmd'], 'rc': res['returncode'], 'log': res['stdout_path']})

    summary = {'root': str(h.root), 'total': runs, 'failures': len(failures), 'failures_detail': failures}
    print(json.dumps(summary, indent=2))
    h.write_summary()

    # cleanup generated target
    try:
        if target.exists():
            shutil.rmtree(target)
    except Exception:
        pass


if __name__ == '__main__':
    main()
