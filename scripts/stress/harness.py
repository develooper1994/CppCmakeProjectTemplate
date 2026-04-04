#!/usr/bin/env python3
"""Lightweight stress-test harness utilities.

Usage: import this module from scenario scripts or run scenario scripts that
use Harness to execute commands, capture outputs and write a summary into
the /tmp workspace created for the run.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class StepResult:
    name: str
    cmd: list[str]
    cwd: str
    returncode: int
    stdout_path: str
    duration_s: float


class Harness:
    def __init__(self, base_tmp: str | Path | None = None, prefix: str = "ccpt-scenario"):
        base = Path(base_tmp) if base_tmp else Path("/tmp")
        ts = int(time.time())
        self.root = base / f"{prefix}-{ts}"
        self.runs_dir = self.root / "runs"
        self.fail_dir = self.root / "failures"
        self.artifacts_dir = self.root / "artifacts"
        for d in (self.root, self.runs_dir, self.fail_dir, self.artifacts_dir):
            d.mkdir(parents=True, exist_ok=True)

        self.tool_script = REPO_ROOT / "scripts" / "tool.py"
        self.python = sys.executable
        self._steps: list[StepResult] = []

    def run_cmd(self, cmd: list[str], cwd: str | Path | None = None, *,
                timeout: int = 120, step_name: str | None = None, use_python: bool = True) -> dict[str, Any]:
        """Execute a command and capture stdout/stderr to a run log.

        - `cmd`: list of argv (if `use_python` True, `cmd` is arguments passed to the python
          interpreter, e.g. `[str(tool_script), 'generate', '--target-dir', '/tmp/...']`).
        - `use_python`: if True, the executed argv is `[python_exe] + cmd`, otherwise `cmd` is run directly.
        """
        cwdp = Path(cwd) if cwd else REPO_ROOT
        argv = ([self.python] + cmd) if use_python else cmd
        start = time.time()
        try:
            proc = subprocess.run(
                [str(a) for a in argv],
                cwd=str(cwdp),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=timeout,
            )
            out = proc.stdout or ""
            rc = proc.returncode
        except subprocess.TimeoutExpired as e:  # pragma: no cover - robust wrapper
            out = (e.stdout or "") + "\n[Timed out]"
            rc = 124
        except FileNotFoundError as e:
            out = f"[FileNotFoundError] {e}\n"
            rc = 127
        dur = time.time() - start

        run_id = int(start * 1000)
        name = step_name or f"run_{run_id}"
        out_path = self.runs_dir / f"{run_id}_{name}.log"
        out_path.write_text(out, encoding="utf-8")

        res = StepResult(
            name=name,
            cmd=[str(c) for c in cmd],
            cwd=str(cwdp),
            returncode=rc,
            stdout_path=str(out_path),
            duration_s=round(dur, 3),
        )
        self._steps.append(res)

        if rc != 0:
            # Save failure metadata for faster repro
            meta = {
                "name": res.name,
                "cmd": res.cmd,
                "cwd": res.cwd,
                "returncode": res.returncode,
                "stdout_path": res.stdout_path,
                "duration_s": res.duration_s,
            }
            fail_path = self.fail_dir / f"{run_id}_{name}.json"
            fail_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

        return {
            "name": res.name,
            "cmd": res.cmd,
            "cwd": res.cwd,
            "returncode": res.returncode,
            "stdout_path": res.stdout_path,
            "duration_s": res.duration_s,
        }

    def summary(self) -> dict[str, Any]:
        total = len(self._steps)
        fails = [s for s in self._steps if s.returncode != 0]
        data = {
            "root": str(self.root),
            "total_steps": total,
            "failures": len(fails),
            "steps": [s.__dict__ for s in self._steps],
        }
        return data

    def write_summary(self) -> None:
        s = self.summary()
        (self.root / "summary.json").write_text(json.dumps(s, indent=2), encoding="utf-8")


if __name__ == "__main__":
    print("Harness module — import and use from scenario scripts.")
