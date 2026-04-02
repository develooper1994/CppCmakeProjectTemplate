"""Shared constants and utility functions for sol subcommands."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from core.utils.common import (
    Logger,
    PROJECT_ROOT,
    json_read_cached,
    json_cache_clear,
)
from core.libpkg.jinja_helpers import (
    render_template_file as _render_template_file,
    JINJA_AVAILABLE as _USE_JINJA_SOL,
)

# ── Constants ─────────────────────────────────────────────────────────────────
TOOLCHAINS_DIR = PROJECT_ROOT / "cmake" / "toolchains"
PRESETS_FILE = PROJECT_ROOT / "CMakePresets.json"
FETCH_DEPS_FILE = PROJECT_ROOT / ".fetch_deps.json"

VALID_COMPILERS = {"gcc", "clang", "msvc"}
VALID_TYPES = {"debug", "release", "relwithdebinfo"}
VALID_LINKS = {"static", "dynamic"}
_BUILD_TYPE = {"debug": "Debug", "release": "Release", "relwithdebinfo": "RelWithDebInfo"}
_SHARED = {"static": "OFF", "dynamic": "ON"}


# ── Preset I/O ────────────────────────────────────────────────────────────────

def load_presets() -> dict:
    if not PRESETS_FILE.exists():
        return {}
    try:
        data = json_read_cached(PRESETS_FILE, default={}) or {}
        return data
    except Exception:
        Logger.error("Failed to parse CMakePresets.json")
        raise


@lru_cache(maxsize=1)
def load_fetch_deps() -> list:
    if not FETCH_DEPS_FILE.exists():
        return []
    try:
        return json.loads(FETCH_DEPS_FILE.read_text(encoding="utf-8"))
    except Exception:
        Logger.error("Failed to parse .fetch_deps.json")
        return []


def save_presets(data: dict) -> None:
    PRESETS_FILE.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    try:
        json_cache_clear(PRESETS_FILE)
    except Exception:
        pass


def _make_preset_name(compiler: str, btype: str, link: str, arch: str) -> str:
    return f"{compiler}-{btype}-{link}-{arch}"


def _generate_custom_gnu(name: str, prefix: str, cpu: str, fpu: str) -> str:
    if _USE_JINJA_SOL:
        return _render_template_file("custom_gnu_toolchain.jinja2", name=name, prefix=prefix, cpu=cpu, fpu=fpu)

    return (
        f"# Custom GNU toolchain generated for {name}\n"
        f"set(CMAKE_SYSTEM_NAME Linux)\n"
        f"set(CMAKE_C_COMPILER {prefix}gcc)\n"
        f"set(CMAKE_CXX_COMPILER {prefix}g++)\n"
    )
