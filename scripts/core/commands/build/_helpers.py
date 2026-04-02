"""Shared constants and utility functions for build subcommands."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Optional

from core.utils.common import (
    Logger,
    PROJECT_ROOT,
    list_presets,
    json_read_cached,
    json_cache_clear,
    get_project_version,
)
from core.libpkg.jinja_helpers import render_template_file

# ── Constants ─────────────────────────────────────────────────────────────────
DEFAULT_PRESET = "gcc-debug-static-x86_64"

EXT_DIR = PROJECT_ROOT / "extension"


# ── Utility functions ─────────────────────────────────────────────────────────


def _sync_version() -> None:
    pkg = EXT_DIR / "package.json"
    if not pkg.exists():
        return
    try:
        data = json_read_cached(pkg, default={}) or {}
    except Exception:
        return
    ver = get_project_version()
    if data.get("version") != ver:
        data["version"] = ver
        pkg.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        try:
            json_cache_clear(pkg)
        except Exception:
            pass
        Logger.info(f"Synchronized extension version -> {ver}")


def _sync_license() -> None:
    src = PROJECT_ROOT / "LICENSE"
    dst = EXT_DIR / "LICENSE"
    if src.exists():
        shutil.copy2(src, dst)


def _choose_preset(preset: Optional[str]) -> str:
    if preset:
        return preset
    presets = list_presets()
    if presets:
        return presets[0]
    return DEFAULT_PRESET


def _generate_clang_tidy(profile: str) -> None:
    """Dynamically generate .clang-tidy based on build profile."""
    try:
        content = render_template_file("clang_tidy.jinja2", profile=profile)
        (PROJECT_ROOT / ".clang-tidy").write_text(content, encoding="utf-8")
        Logger.debug(f"Generated .clang-tidy for profile: {profile}")
    except Exception as e:
        Logger.warn(f"Failed to generate .clang-tidy: {e}")
