#!/usr/bin/env python3
"""
core/utils/common.py — Shared utilities for the toolset.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import NoReturn, Any

class GlobalConfig:
    VERBOSE: bool = False
    YES: bool = False
    JSON: bool = False
    DRY_RUN: bool = False
    VERSION: str = "1.0.0"

@dataclass
class CLIResult:
    success: bool
    code: int = 0
    message: str = ""
    data: Any = None
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def exit(self):
        if GlobalConfig.JSON:
            print(json.dumps(asdict(self), indent=2, ensure_ascii=False))
        else:
            if self.message:
                if self.success: Logger.success(self.message)
                else: Logger.error(self.message)
        sys.exit(self.code)

class Logger:
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

    @staticmethod
    def _log(level: str, msg: str, color: str = ""):
        if GlobalConfig.JSON: return
        prefix = f"[{level}]"
        print(f"{color}{prefix:<8} {msg}{Logger.RESET}")
        try:
            log_file = PROJECT_ROOT / "build_logs" / "tool.log"
            log_file.parent.mkdir(exist_ok=True)
            with open(log_file, "a", encoding="utf-8") as f:
                full_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"{full_ts} {level:<8} {msg}\n")
        except Exception: pass

    @staticmethod
    def info(msg: str): Logger._log("INFO", msg, Logger.BLUE)
    @staticmethod
    def success(msg: str): Logger._log("SUCCESS", msg, Logger.GREEN)
    @staticmethod
    def warn(msg: str): Logger._log("WARN", msg, Logger.YELLOW)
    @staticmethod
    def error(msg: str): Logger._log("ERROR", msg, Logger.RED)
    @staticmethod
    def debug(msg: str):
        if GlobalConfig.VERBOSE: Logger._log("DEBUG", msg, Logger.BOLD)

def find_project_root(start: Path) -> Path:
    p = start.resolve()
    if p.is_file(): p = p.parent
    while True:
        if (p / "libs").is_dir() and (p / "scripts").is_dir(): return p
        if p.parent == p: raise RuntimeError("Project root not found.")
        p = p.parent

PROJECT_ROOT: Path = find_project_root(Path(__file__).resolve())

def run_proc(cmd: list[str], check: bool = True, cwd: Path = PROJECT_ROOT) -> int:
    Logger.debug(f"Executing: {' '.join(str(c) for c in cmd)}")
    result = subprocess.run(cmd, cwd=cwd)
    if check and result.returncode != 0:
        Logger.error(f"Execution failed (code {result.returncode})")
        sys.exit(result.returncode)
    return result.returncode

def fail(msg: str, code: int = 1) -> NoReturn:
    CLIResult(success=False, code=code, message=msg).exit()

def header(title: str, subtitle: str | None = None) -> None:
    print(f"{Logger.BOLD}{'=' * 52}{Logger.RESET}")
    print(f"  {Logger.BOLD}{title}{Logger.RESET}")
    if subtitle: print(f"  {subtitle}")
    print(f"  Root: {PROJECT_ROOT}")
    print(f"{Logger.BOLD}{'=' * 52}{Logger.RESET}")

def list_presets() -> list[str]:
    presets_file = PROJECT_ROOT / "CMakePresets.json"
    if not presets_file.exists(): return []
    data = json.loads(presets_file.read_text(encoding="utf-8"))
    return [p["name"] for p in data.get("configurePresets", []) if not p.get("hidden", False)]
