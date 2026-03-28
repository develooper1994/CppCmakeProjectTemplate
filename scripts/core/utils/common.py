#!/usr/bin/env python3
"""
core/utils/common.py — Shared utilities for the toolset.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import shutil
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import NoReturn, Any
from functools import lru_cache

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
            LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                full_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"{full_ts} {level:<8} {msg}\n")
        except Exception:
            pass

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
LOG_FILE: Path = PROJECT_ROOT / "build_logs" / "tool.log"

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

@lru_cache(maxsize=None)
def list_presets() -> list[str]:
    presets_file = PROJECT_ROOT / "CMakePresets.json"
    if not presets_file.exists(): return []
    data = json.loads(presets_file.read_text(encoding="utf-8"))
    return [p["name"] for p in data.get("configurePresets", []) if not p.get("hidden", False)]


@lru_cache(maxsize=None)
def get_project_version(root: Path = PROJECT_ROOT) -> str:
    """Resolve project version from CMakeLists.txt or git tags, fallback '0.0.0'."""
    cmake_path = root / "CMakeLists.txt"
    if cmake_path.exists():
        clean = re.sub(r'#.*', '', cmake_path.read_text(encoding="utf-8"))
        m = re.search(r'project\s*\([^)]*VERSION\s+([\d.]+)', clean, re.IGNORECASE | re.DOTALL)
        if m:
            return m.group(1)
    try:
        tag = subprocess.check_output([
            "git", "describe", "--tags", "--abbrev=0"
        ], cwd=root, stderr=subprocess.DEVNULL).decode().strip()
        return re.sub(r'^v', '', tag)
    except Exception:
        pass
    return "0.0.0"


@lru_cache(maxsize=None)
def get_project_name(root: Path = PROJECT_ROOT) -> str:
    cmake = (root / "CMakeLists.txt").read_text(encoding="utf-8") if (root / "CMakeLists.txt").exists() else ""
    m = re.search(r'project\s*\(\s*(\S+)', cmake, re.IGNORECASE)
    return m.group(1) if m else "CppProject"


# Small JSON file cache to avoid repeated parsing of small config files during a single run.
# Cached by file path and mtime; use `json_cache_clear()` to invalidate after writes.
_JSON_CACHE: dict = {}


def json_read_cached(path: Path, default=None):
    try:
        if not path.exists():
            return default
        mtime = path.stat().st_mtime
        key = str(path)
        entry = _JSON_CACHE.get(key)
        if entry and entry[0] == mtime:
            return entry[1]
        try:
            val = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            val = default
        _JSON_CACHE[key] = (mtime, val)
        return val
    except Exception:
        return default


def json_cache_clear(path: Path | None = None) -> None:
    try:
        if path is None:
            _JSON_CACHE.clear()
        else:
            _JSON_CACHE.pop(str(path), None)
    except Exception:
        pass


# Session persistence helpers (shared between tool and TUI)
SESSION_FILE: Path = PROJECT_ROOT / ".session.json"

def load_session() -> dict:
    """Load session data from the shared session file.

    Returns an empty dict when no session file exists or parsing fails.
    """
    try:
        # Backwards compatibility: prefer .session.json, fall back to .tui_session.json
        alt = PROJECT_ROOT / ".tui_session.json"
        target = SESSION_FILE if SESSION_FILE.exists() else (alt if alt.exists() else None)
        if not target:
            return {}
        return json.loads(target.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_session(data: dict) -> None:
    """Save the given session dict to the shared session file.

    This overwrites the file atomically.
    """
    try:
        SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
        SESSION_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    except Exception:
        pass
    # Also write legacy TUI session file for compatibility
    try:
        alt = PROJECT_ROOT / ".tui_session.json"
        alt.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    except Exception:
        pass


def backup_session() -> Path | None:
    """Create a timestamped backup of the current session file.

    Returns the backup path or None when no session file existed.
    """
    try:
        if not SESSION_FILE.exists():
            return None
        ts = datetime.now().strftime("%Y%m%dT%H%M%S")
        bak = SESSION_FILE.with_name(SESSION_FILE.name + f".{ts}.bak")
        shutil.copy2(SESSION_FILE, bak)
        return bak
    except Exception:
        return None
