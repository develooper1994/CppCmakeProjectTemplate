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
from typing import NoReturn, Any, Tuple
from functools import lru_cache

class GlobalConfig:
    VERBOSE: bool = False
    YES: bool = False
    JSON: bool = False
    DRY_RUN: bool = False
    VERSION: str = "1.0.5"

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
                if self.success:
                    Logger.success(self.message)
                else:
                    Logger.error(self.message)
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
        if GlobalConfig.JSON:
            return
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
    def info(msg: str):
        Logger._log("INFO", msg, Logger.BLUE)

    @staticmethod
    def success(msg: str):
        Logger._log("SUCCESS", msg, Logger.GREEN)

    @staticmethod
    def warn(msg: str):
        Logger._log("WARN", msg, Logger.YELLOW)

    @staticmethod
    def error(msg: str):
        Logger._log("ERROR", msg, Logger.RED)

    @staticmethod
    def debug(msg: str):
        if GlobalConfig.VERBOSE:
            Logger._log("DEBUG", msg, Logger.BOLD)

def find_project_root(start: Path) -> Path:
    p = start.resolve()
    if p.is_file():
        p = p.parent
    while True:
        if (p / "libs").is_dir() and (p / "scripts").is_dir():
            return p
        if p.parent == p:
            raise RuntimeError("Project root not found.")
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


def run_capture(cmd: list[str], cwd: Path = PROJECT_ROOT, *, strip_ansi: bool = False, text: bool = True) -> Tuple[str, int]:
    """Run a command and return (stdout, returncode).

    - `cmd` is a list of command parts (same as subprocess.run).
    - `cwd` defaults to the repository root as determined by `PROJECT_ROOT`.
    - `strip_ansi` will remove common ANSI color/escape sequences.
    - `text` controls whether to run in text mode (True by default).
    """
    try:
        Logger.debug(f"run_capture: {' '.join(str(c) for c in cmd)}")
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=text,
            check=False,
        )
        out = proc.stdout or ""
        if strip_ansi:
            out = re.sub(r'\x1b\[[0-9;]*m', '', out)
        return out.strip(), proc.returncode
    except Exception as e:  # pragma: no cover - best-effort wrapper
        return f"Exception invoking command: {e}", 1

def fail(msg: str, code: int = 1) -> NoReturn:
    # Use CLIResult to format/print the error, then explicitly raise
    # SystemExit so static analyzers understand this function does not return.
    CLIResult(success=False, code=code, message=msg).exit()
    raise SystemExit(code)

def header(title: str, subtitle: str | None = None) -> None:
    print(f"{Logger.BOLD}{'=' * 52}{Logger.RESET}")
    print(f"  {Logger.BOLD}{title}{Logger.RESET}")
    if subtitle:
        print(f"  {subtitle}")
    print(f"  Root: {PROJECT_ROOT}")
    print(f"{Logger.BOLD}{'=' * 52}{Logger.RESET}")

@lru_cache(maxsize=None)
def list_presets() -> list[str]:
    presets_file = PROJECT_ROOT / "CMakePresets.json"
    if not presets_file.exists():
        return []
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
        out, rc = run_capture(["git", "describe", "--tags", "--abbrev=0"], cwd=root)
        if rc == 0 and out:
            tag = out.strip()
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
        # Use the canonical shared session file only
        if not SESSION_FILE.exists():
            return {}
        return json.loads(SESSION_FILE.read_text(encoding="utf-8"))
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
    # Do not write a separate TUI session file; prefer the shared `SESSION_FILE` only.


def find_missing_binaries(binaries: dict[str, str]) -> dict[str, str]:
    """Check for existence of binaries. Returns dict of missing {bin: pkg_name}."""
    missing = {}
    for bin_name, pkg in binaries.items():
        if shutil.which(bin_name) is None:
            missing[bin_name] = pkg
    return missing


def create_venv(env_dir: Path, recreate: bool = False) -> Path:
    """Create a virtual environment. Returns path to its Python executable."""
    import venv
    env_dir = env_dir.resolve()
    if env_dir.exists():
        if recreate:
            Logger.info(f"Removing existing venv at {env_dir}")
            shutil.rmtree(env_dir)
        else:
            Logger.info(f"Virtualenv already exists at {env_dir}")
            return _get_venv_python(env_dir)

    Logger.info(f"Creating venv at {env_dir}")
    builder = venv.EnvBuilder(with_pip=True)
    builder.create(str(env_dir))

    py = _get_venv_python(env_dir)
    if not py.exists():
        raise FileNotFoundError(f"Python not found in created venv: {py}")

    # Upgrade pip
    try:
        run_proc([str(py), "-m", "pip", "install", "--upgrade", "pip", "wheel", "setuptools"], check=False)
    except Exception:
        pass

    return py


def _get_venv_python(env_dir: Path) -> Path:
    import platform
    if platform.system() == "Windows":
        return env_dir / "Scripts" / "python.exe"
    return env_dir / "bin" / "python"


def install_python_requirements(py_exe: Path, req_file: Path) -> None:
    if not req_file.exists():
        Logger.warn(f"No {req_file.name} found; skipping install")
        return
    Logger.info(f"Installing requirements from {req_file.name}")
    run_proc([str(py_exe), "-m", "pip", "install", "-r", str(req_file)])


def print_venv_activation(env_dir: Path) -> None:
    import platform
    if platform.system() == "Windows":
        print(f"To activate (PowerShell): {env_dir / 'Scripts' / 'Activate.ps1'}")
        print(f"To activate (cmd): {env_dir / 'Scripts' / 'activate.bat'}")
    else:
        print(f"To activate: source {env_dir / 'bin' / 'activate'}")
