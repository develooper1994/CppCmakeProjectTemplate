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
    # If true, scripts may attempt to provision/install required tools/deps
    INSTALL: bool = False
    # When used with --install, recreate the venv if True
    INSTALL_RECREATE: bool = False
    # CI-level flags
    SKIP_CI: bool = False
    CI_MODE: str | None = None       # smoke | full | nightly
    REPORT_ARTIFACT: str | None = None
    RETAIN_DAYS: int | None = None
    VERSION: str = "1.0.5"
    # Defaults populated by config_loader from tool.toml
    DEFAULT_PRESET: str = ""
    PERF_SIZE_THRESHOLD_PCT: float = 10.0
    PERF_TIME_THRESHOLD_PCT: float = 20.0
    SECURITY_FAIL_SEVERITY: str = "HIGH"
    DOC_SERVE_PORT: int = 8080
    DOC_SERVE_OPEN: bool = False

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

# If repository has a central VERSION file, use it as the authoritative
# source of truth for the toolset version. This makes it easy to keep
# scripts, CMake and packaging in sync by updating a single file.
try:
    version_file = PROJECT_ROOT / "VERSION"
    if version_file.exists():
        GlobalConfig.VERSION = version_file.read_text(encoding="utf-8").strip()
except Exception:
    # best-effort: leave default in place
    pass

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
# Session state is stored in the [session] section of tool.toml so that all
# tooling shares a single configuration file (no separate .session.json).
TOOL_TOML_FILE: Path = PROJECT_ROOT / "tool.toml"


def _ensure_tool_toml() -> Path:
    """Create a minimal tool.toml if it does not exist yet."""
    if not TOOL_TOML_FILE.exists():
        TOOL_TOML_FILE.write_text(
            "# tool.toml — auto-generated minimal configuration\n\n"
            "[session]\n",
            encoding="utf-8",
        )
    return TOOL_TOML_FILE


def _read_toml_text() -> str:
    """Return the raw text of tool.toml (creating the file when absent)."""
    _ensure_tool_toml()
    return TOOL_TOML_FILE.read_text(encoding="utf-8")


def _write_toml_text(text: str) -> None:
    """Write *text* back to tool.toml."""
    TOOL_TOML_FILE.write_text(text, encoding="utf-8")


def load_session() -> dict:
    """Load the ``[session]`` section from tool.toml.

    Returns an empty dict when no session section exists or parsing fails.
    """
    try:
        _ensure_tool_toml()
        try:
            import tomlkit
            doc = tomlkit.parse(_read_toml_text())
            sess = doc.get("session")
            if sess is None:
                return {}
            # tomlkit containers → plain dict
            return {k: v for k, v in sess.items()}
        except ImportError:
            pass
        # Fallback: stdlib tomllib (read-only, 3.11+) or tomli
        try:
            import tomllib  # type: ignore[import-untyped]
        except ImportError:
            try:
                import tomli as tomllib  # type: ignore[no-redef]
            except ImportError:
                tomllib = None  # type: ignore[assignment]
        if tomllib is not None:
            data = tomllib.loads(_read_toml_text())
            return dict(data.get("session", {}))
        # Last resort: line-based extraction
        return _minimal_session_read()
    except Exception:
        return {}


def save_session(data: dict) -> None:
    """Save *data* into the ``[session]`` section of tool.toml.

    Uses ``tomlkit`` for comment-preserving writes when available;
    falls back to a simple line-based updater otherwise.
    """
    try:
        _ensure_tool_toml()
        try:
            import tomlkit
            doc = tomlkit.parse(_read_toml_text())
            if "session" not in doc:
                doc.add(tomlkit.nl())
                doc.add(tomlkit.comment(
                    " [session] — Runtime session state (managed by tool)"))
                doc.add("session", tomlkit.table())
            tbl = doc["session"]
            # Clear existing keys then set new ones
            for k in list(tbl):
                del tbl[k]
            for k, v in data.items():
                tbl[k] = v
            _write_toml_text(tomlkit.dumps(doc))
            return
        except ImportError:
            pass
        # Fallback: line-based updater
        _minimal_session_write(data)
    except Exception:
        pass


def backup_session() -> Path | None:
    """Create a timestamped backup of tool.toml.

    Returns the backup path on success, or None if the file is absent.
    """
    if not TOOL_TOML_FILE.exists():
        return None
    try:
        import time as _time
        ts = int(_time.time())
        bak = TOOL_TOML_FILE.with_suffix(f".{ts}.bak.toml")
        bak.write_bytes(TOOL_TOML_FILE.read_bytes())
        return bak
    except Exception:
        return None


# -- Minimal fallback helpers (no tomlkit) ---------------------------------

def _minimal_session_read() -> dict:
    """Extract ``[session]`` key-value pairs without a full TOML parser."""
    from core.utils.config_loader import _coerce
    result: dict = {}
    in_session = False
    for raw_line in _read_toml_text().splitlines():
        stripped = raw_line.strip()
        if stripped.startswith("["):
            in_session = stripped == "[session]"
            continue
        if not in_session:
            continue
        line = stripped.split("#")[0].strip()
        if not line or "=" not in line:
            continue
        k, _, v = line.partition("=")
        result[k.strip()] = _coerce(v.strip())
    return result


def _minimal_session_write(data: dict) -> None:
    """Replace (or append) the ``[session]`` section using plain text ops."""
    lines = _read_toml_text().splitlines(keepends=True)
    new_lines: list[str] = []
    in_session = False
    session_written = False
    for line in lines:
        stripped = line.strip()
        if stripped == "[session]":
            in_session = True
            session_written = True
            new_lines.append(line)
            for k, v in data.items():
                new_lines.append(f"{k} = {_toml_value(v)}\n")
            continue
        if in_session:
            if stripped.startswith("["):
                in_session = False
                new_lines.append(line)
            # skip old session keys
            continue
        new_lines.append(line)
    if not session_written:
        if new_lines and not new_lines[-1].endswith("\n"):
            new_lines.append("\n")
        new_lines.append("\n[session]\n")
        for k, v in data.items():
            new_lines.append(f"{k} = {_toml_value(v)}\n")
    _write_toml_text("".join(new_lines))


def _toml_value(v: object) -> str:
    """Format a Python value as a TOML literal."""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        return str(v)
    if isinstance(v, str):
        return json.dumps(v)  # proper quoting / escaping
    if isinstance(v, list):
        return "[" + ", ".join(_toml_value(i) for i in v) + "]"
    return json.dumps(str(v))


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


def install_dev_env(env_dir: Path | None = None, recreate: bool = False, req_file: Path | None = None) -> Path:
    """Create a local development virtualenv and install dev requirements.

    - `env_dir`: path to the virtualenv directory (defaults to `PROJECT_ROOT/.venv`).
    - `recreate`: if True, recreate the venv even if it exists.
    - `req_file`: Path to requirements file (defaults to `requirements-dev.txt`).

    Returns the Python executable Path inside the created environment.
    """
    env_dir = Path(env_dir) if env_dir is not None else PROJECT_ROOT / ".venv"
    req_file = Path(req_file) if req_file is not None else PROJECT_ROOT / "requirements-dev.txt"
    Logger.info(f"Ensuring development environment at {env_dir}")
    py = create_venv(env_dir, recreate=recreate)
    try:
        install_python_requirements(py, req_file)
    except Exception as e:
        Logger.warn(f"Failed to install some dev requirements: {e}")
    print_venv_activation(env_dir)
    return py
