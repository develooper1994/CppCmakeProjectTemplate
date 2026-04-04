"""
core/utils/config_loader.py — Central configuration manager for all tooling.

Responsibilities
----------------
  1. Read and cache ``tool.toml`` (``load_tool_config``, ``get_config``).
  2. Apply tool.toml values into ``GlobalConfig`` (``apply_to_global_config``).
  3. Manage the ``[session]`` section in tool.toml as the single runtime-state
     store for all scripts (``load_session``, ``save_session``, ``backup_session``).

Priority (highest → lowest)
----------------------------
  1. CLI flags
  2. Environment variables  (TOOL_<SECTION>_<KEY>=value)
  3. tool.toml values
  4. Built-in defaults (GlobalConfig class attributes)

Usage
-----
    from core.utils.config_loader import load_tool_config, get_config, load_session
    cfg    = load_tool_config()          # reads / caches tool.toml
    preset = get_config("build", "preset")
    sess   = load_session()             # reads [session] section
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ImportError:
        tomllib = None  # type: ignore[assignment]

# --- DYNAMIC CONFIG DISCOVERY ---
def get_project_root() -> Path:
    """Return the currently active project root from common utilities."""
    from core.utils import common
    return common.PROJECT_ROOT

def get_tool_toml_path() -> Path:
    """Return the current tool.toml path based on project root."""
    return get_project_root() / "tool.toml"

# Module-level cache — reset when PROJECT_ROOT changes
_config: dict[str, Any] = {}
_loaded_from: Path | None = None


def load_tool_config(path: Path | None = None) -> dict[str, Any]:
    """
    Load tool.toml (or *path*) and apply environment variable overrides.

    Returns the merged config dict.  On parse error or missing file,
    returns an empty dict (never raises — callers should not crash if
    tool.toml is absent).
    """
    global _config, _loaded_from
    
    cfg_path = path or get_tool_toml_path()
    
    # Invalidate cache if we are loading from a different path
    if _loaded_from != cfg_path:
        _config = {}
        _loaded_from = None

    if _config and _loaded_from == cfg_path:
        return _config

    raw: dict[str, Any] = {}

    if cfg_path.exists():
        if tomllib is None:
            # Python < 3.11 without tomli — attempt a minimal TOML parser
            raw = _minimal_toml_parse(cfg_path)
        else:
            try:
                raw = tomllib.loads(cfg_path.read_text(encoding="utf-8"))
            except Exception as exc:
                import logging
                logging.getLogger(__name__).warning("tool.toml parse error: %s", exc)
                raw = {}

    # Apply environment variable overrides: TOOL_<SECTION>_<KEY>=value
    for key, val in os.environ.items():
        if not key.startswith("TOOL_"):
            continue
        parts = key.lower().split("_", 2)  # ["tool", section, rest]
        if len(parts) < 3:
            continue
        _, section, opt = parts
        if section not in raw:
            raw[section] = {}
        raw[section][opt] = _coerce(val)

    _config = raw
    _loaded_from = cfg_path
    return _config


def get_config(section: str, key: str, default: Any = None) -> Any:
    """
    Retrieve a single value from the loaded config.

    Example::

        port = get_config("doc", "serve_port", 8080)
    """
    cfg = load_tool_config()
    return cfg.get(section, {}).get(key, default)


def apply_to_global_config() -> None:
    """
    Push tool.toml values into GlobalConfig where they haven't already
    been set via CLI flags.  Called once by tool.py dispatcher before
    command dispatch.
    """
    from core.utils.common import GlobalConfig  # lazy import to avoid circular

    cfg = load_tool_config()

    tool_sec = cfg.get("tool", {})
    if not GlobalConfig.VERBOSE and "log_format" in tool_sec:
        pass  # log_format controls format, not verbosity — skip

    build_sec = cfg.get("build", {})
    if "preset" in build_sec and not getattr(GlobalConfig, "DEFAULT_PRESET", None):
        GlobalConfig.DEFAULT_PRESET = build_sec["preset"]

    # Perf budget thresholds — stored as class attributes for perf.py
    perf_sec = cfg.get("perf", {})
    GlobalConfig.PERF_SIZE_THRESHOLD_PCT = float(perf_sec.get("size_threshold_pct", 10.0))
    GlobalConfig.PERF_TIME_THRESHOLD_PCT = float(perf_sec.get("time_threshold_pct", 20.0))

    # Security defaults
    sec_sec = cfg.get("security", {})
    if not getattr(GlobalConfig, "SECURITY_FAIL_SEVERITY", None):
        GlobalConfig.SECURITY_FAIL_SEVERITY = sec_sec.get("fail_on_severity", "HIGH")

    # Doc defaults
    doc_sec = cfg.get("doc", {})
    GlobalConfig.DOC_SERVE_PORT = int(doc_sec.get("serve_port", 8080))
    GlobalConfig.DOC_SERVE_OPEN = bool(doc_sec.get("serve_open_browser", False))


# ---------------------------------------------------------------------------
# Minimal TOML parser (fallback when neither tomllib nor tomli is available).
# Handles only simple key = value, [section], and # comments.
# ---------------------------------------------------------------------------

def _minimal_toml_parse(path: Path) -> dict[str, Any]:
    """Parse a subset of TOML sufficient for tool.toml (no arrays-of-tables)."""
    result: dict[str, Any] = {}
    section: str = ""
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#")[0].strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].strip()
            result.setdefault(section, {})
        elif "=" in line and section:
            k, _, v = line.partition("=")
            result[section][k.strip()] = _coerce(v.strip())
    return result


def _coerce(val: str) -> Any:
    """Convert string value to Python native type."""
    # Strip surrounding quotes
    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
        return val[1:-1]
    if val.lower() in ("true", "yes"):
        return True
    if val.lower() in ("false", "no"):
        return False
    # List (simplified — single-line arrays only)
    if val.startswith("[") and val.endswith("]"):
        inner = val[1:-1].strip()
        if not inner:
            return []
        return [_coerce(item.strip()) for item in inner.split(",")]
    try:
        return int(val)
    except ValueError:
        pass
    try:
        return float(val)
    except ValueError:
        pass
    return val


# ---------------------------------------------------------------------------
# Session persistence — read/write the [session] section of tool.toml.
#
# Every script reads and writes only its own keys.  All TOML I/O is
# centralised here so that common.py stays focused on process utilities.
# ---------------------------------------------------------------------------

def _ensure_tool_toml() -> Path:
    """Create a minimal tool.toml when the file does not exist yet."""
    cfg_path = get_tool_toml_path()
    if not cfg_path.exists():
        cfg_path.write_text(
            "# tool.toml — auto-generated minimal configuration\n\n"
            "[session]\n",
            encoding="utf-8",
        )
    return cfg_path


def _read_toml_text() -> str:
    """Return the raw text of tool.toml, creating the file if absent."""
    return _ensure_tool_toml().read_text(encoding="utf-8")


def _write_toml_text(text: str) -> None:
    """Write *text* back to tool.toml and invalidate the in-process read cache."""
    global _loaded_from
    cfg_path = _ensure_tool_toml()
    cfg_path.write_text(text, encoding="utf-8")
    _loaded_from = None  # force re-read


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
            return {} if sess is None else {k: v for k, v in sess.items()}
        except ImportError:
            pass
        if tomllib is not None:
            data = tomllib.loads(_read_toml_text())
            return dict(data.get("session", {}))
        return _minimal_session_read()
    except Exception:
        return {}


def save_session(data: dict) -> None:
    """Write *data* into the ``[session]`` section of tool.toml.

    Uses ``tomlkit`` for comment-preserving writes when available; falls back
    to a line-based updater so the rest of the file is never corrupted.
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
            for k in list(tbl):
                del tbl[k]
            for k, v in data.items():
                tbl[k] = v
            _write_toml_text(tomlkit.dumps(doc))
            return
        except ImportError:
            pass
        _minimal_session_write(data)
    except Exception:
        pass


def backup_session() -> Path | None:
    """Create a timestamped backup of tool.toml.

    Returns the backup path on success, or *None* when the file is absent.
    """
    cfg_path = get_tool_toml_path()
    if not cfg_path.exists():
        return None
    try:
        import time as _time
        ts = int(_time.time())
        bak = cfg_path.with_suffix(f".{ts}.bak.toml")
        bak.write_bytes(cfg_path.read_bytes())
        return bak
    except Exception:
        return None


def _minimal_session_read() -> dict:
    """Extract ``[session]`` key-value pairs without a full TOML parser."""
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
            # skip old session key lines
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
        return json.dumps(v)
    if isinstance(v, list):
        return "[" + ", ".join(_toml_value(i) for i in v) + "]"
    return json.dumps(str(v))
