#!/usr/bin/env python3
"""Human-like workflow stress scenario.

1. Generate a new C++ project using `tool generate` into a temporary dir under /tmp.
2. Inspect the generated project for an executable target (attempts common locations).
3. Configure and build the project with CMake in a local build dir.
4. Run the produced executable with several argument combinations and record outputs.

This script uses the Harness utilities so outputs and logs are written under /tmp.
"""
from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
HARNESS_PATH = REPO_ROOT / "scripts" / "stress" / "harness.py"

import importlib.util
spec = importlib.util.spec_from_file_location("ccpt_harness", str(HARNESS_PATH))
hmod = importlib.util.module_from_spec(spec)
import sys as _sys
_sys.modules[spec.name] = hmod
spec.loader.exec_module(hmod)
Harness = hmod.Harness


def find_executable_bin(target_dir: Path) -> Path | None:
    """Try to locate a built executable in typical locations.

    Returns a Path to the exe or None.
    """
    # Common build outputs: build/<preset>/bin, build/, bin/, out/, a local app folder
    candidates = [
        target_dir / 'build',
        target_dir / 'bin',
        target_dir / 'out',
        target_dir / 'apps',
        target_dir,
    ]
    exts = ["", ".out"]
    prioritized = []
    others = []
    for base in candidates:
        if not base.exists():
            continue
        for p in base.rglob('*'):
            if not p.exists() or not p.is_file():
                continue
            # Skip common source/config files which are not executables
            if p.suffix.lower() in {'.cpp', '.cc', '.c', '.cxx', '.h', '.hpp', '.in', '.cmake', '.py', '.md', '.txt', '.json'}:
                continue
            # Classify by location: prefer files under an 'apps' or 'bin' directory
            parts = [s.lower() for s in p.parts]
            score = 0
            if 'apps' in parts or 'app' in parts:
                score += 10
            if 'bin' in parts or 'out' in parts:
                score += 5
            # Prefer files that look like produced app binaries (names starting with main or the app name)
            if p.name.startswith('main') or p.name.startswith('demo') or p.name.startswith('gui'):
                score += 3
            # Prefer actual executable bit
            try:
                if p.stat().st_mode & 0o111:
                    score += 2
            except Exception:
                pass

            # Prefer native ELF binaries (linux) by checking magic header
            try:
                with p.open('rb') as fh:
                    hdr = fh.read(4)
                    if hdr == b'\x7fELF':
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
        # prefer any executable-like file
        others.sort(key=lambda x: (-x[0], str(x[1])))
        return others[0][1]
    return None


def main():
    h = Harness()
    tool = str(h.tool_script)

    # 1) Generate project into a fresh tmp dir
    target = Path(h.artifacts_dir) / 'generated_project'
    if target.exists():
        shutil.rmtree(target)
    argv = [tool, 'generate', '--profile', 'minimal', '--target-dir', str(target)]
    print('Generating project into:', target)
    r = h.run_cmd(argv, cwd=REPO_ROOT, step_name='generate_project')
    print('generate rc=', r['returncode'])

    # 2) Quick scan for CMakeLists to verify generation
    cmake_ok = (target / 'CMakeLists.txt').exists()
    print('CMakeLists.txt present:', cmake_ok)


    # Move/copy any generated `scripts/` to an isolated location so they don't
    # mix with repository scripts. We copy to preserve the original while
    # keeping a dedicated copy for inspection.
    scripts_src = target / 'scripts'
    scripts_dest = Path(h.artifacts_dir) / 'generated_scripts'
    copied_scripts = False
    if scripts_src.exists() and scripts_src.is_dir():
        if scripts_dest.exists():
            shutil.rmtree(scripts_dest)
        shutil.copytree(scripts_src, scripts_dest)
        print('Copied generated scripts to:', scripts_dest)
        copied_scripts = True
    # 3) Configure and build with CMake
    # 3) Configure, build and exercise the produced binary. Use a try/finally
    #    so we can clean up generated directories afterwards per request.
    build_dir = target / 'build'
    build_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Configure
        cmd_cfg = [
            'cmake', '-S', str(target), '-B', str(build_dir), '-DCMAKE_BUILD_TYPE=Release',
            '-DENABLE_UNIT_TESTS=OFF', '-DENABLE_GTEST=OFF', '-DENABLE_DOCS=OFF'
        ]
        h.run_cmd(cmd_cfg, cwd=target, use_python=False, step_name='cmake_configure', timeout=300)

        # Build
        cmd_build = ['cmake', '--build', str(build_dir), '--config', 'Release', '--', '-j2']
        h.run_cmd(cmd_build, cwd=target, use_python=False, step_name='cmake_build', timeout=600)

        # 4) Find an executable and run with argument combos
        exe = find_executable_bin(target)
        if exe is None:
            print('No executable found; listing build tree for debugging')
            for p in (target).rglob('*'):
                print(p)
            h.write_summary()
            print('Summary at', h.root)
            return

        print('Found executable:', exe)

        arg_matrix = [
            [],
            ['-h'],
            ['--help'],
            ['--version'],
            ['--foo', 'bar'],
            ['--flag', '--opt=42'],
        ]
        for idx, args in enumerate(arg_matrix, start=1):
            argv = [str(exe)] + args
            step = f'run_exe_{idx}'
            print('Running', ' '.join(argv))
            # run directly (not via python)
            h.run_cmd(argv, cwd=target, use_python=False, step_name=step, timeout=60)

        h.write_summary()
        print('Scenario complete. Summary:', json.dumps(h.summary(), indent=2))
    finally:
        # Clean up generated directories as requested (preserve run logs)
        print('Cleaning up generated directories...')
        try:
            if target.exists():
                shutil.rmtree(target)
                print('Removed:', target)
        except Exception as e:
            print('Failed to remove target:', e)
        if copied_scripts and scripts_dest.exists():
            try:
                shutil.rmtree(scripts_dest)
                print('Removed copied scripts:', scripts_dest)
            except Exception as e:
                print('Failed to remove copied scripts:', e)
        print('Cleanup complete. Logs remain at:', h.root)
    print('Scenario complete. Summary:', json.dumps(h.summary(), indent=2))


if __name__ == '__main__':
    main()
