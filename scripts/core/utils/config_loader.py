"""
core/utils/config_loader.py — Load and merge tool.toml into GlobalConfig.

Priority (highest → lowest):
  1. CLI flags
  2. Environment variables  (TOOL_<SECTION>_<KEY>=value)
  3. tool.toml values
  4. Built-in defaults (GlobalConfig class attributes)

Usage
-----
    from core.utils.config_loader import load_tool_config, get_config
    cfg = load_tool_config()           # reads tool.toml from project root
    preset = get_config("build", "preset")
"""
from __future__ import annotations

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

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
TOOL_TOML = PROJECT_ROOT / "tool.toml"

# Module-level cache — loaded once per process
_config: dict[str, Any] = {}
_loaded: bool = False


def load_tool_config(path: Path | None = None) -> dict[str, Any]:
    """
    Load tool.toml (or *path*) and apply environment variable overrides.

    Returns the merged config dict.  On parse error or missing file,
    returns an empty dict (never raises — callers should not crash if
    tool.toml is absent).
    """
    global _config, _loaded
    if _loaded:
        return _config

    cfg_path = path or TOOL_TOML
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
    _loaded = True
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
