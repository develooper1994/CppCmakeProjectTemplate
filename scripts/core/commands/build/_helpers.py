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
TEMPLATE_DIR = EXT_DIR / "templates"

EXT_INCLUDE = [
    "CMakeLists.txt", "CMakePresets.json", "conanfile.py", "vcpkg.json",
    "docker", "LICENSE", "README.md", "AGENTS.md", "GEMINI.md",
    "MASTER_GENERATOR_PROMPT.md", "cmake", "apps", "libs", "tests", "scripts", "docs",
]

EXT_EXCLUDE = {
    "build", "build_logs", "__pycache__", ".cache", "extension",
}


# ── Utility functions ─────────────────────────────────────────────────────────

def _is_excluded(rel: str) -> bool:
    # Normalize to forward slashes
    r = rel.replace("\\", "/")
    if r in EXT_EXCLUDE:
        return True
    for e in EXT_EXCLUDE:
        if r.startswith(e + "/"):
            return True
    return False


def _sync_templates() -> int:
    """Copy project files into extension templates directory, excluding dev files.
    Returns number of files copied."""
    # Incremental sync: avoid full removal/copy when files haven't changed.
    TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
    expected = set()
    copied = 0

    def _should_copy(src_path: Path, dst_path: Path) -> bool:
        if not dst_path.exists():
            return True
        try:
            s = src_path.stat()
            d = dst_path.stat()
            # If size and mtime match (to second), skip copy
            if s.st_size == d.st_size and int(s.st_mtime) == int(d.st_mtime):
                return False
        except Exception:
            return True
        return True

    for item in EXT_INCLUDE:
        src = PROJECT_ROOT / item
        if not src.exists():
            continue
        if src.is_file():
            rel = item
            if _is_excluded(rel):
                continue
            dst = TEMPLATE_DIR / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            expected.add(dst.relative_to(TEMPLATE_DIR).as_posix())
            if _should_copy(src, dst):
                try:
                    shutil.copy2(src, dst)
                    copied += 1
                except Exception:
                    pass
            continue
        # directory
        for f in src.rglob("*"):
            if f.is_file():
                rel = f.relative_to(PROJECT_ROOT).as_posix()
                if _is_excluded(rel):
                    continue
                dst = TEMPLATE_DIR / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                expected.add(dst.relative_to(TEMPLATE_DIR).as_posix())
                if _should_copy(f, dst):
                    try:
                        shutil.copy2(f, dst)
                        copied += 1
                    except Exception:
                        pass

    # Remove stale files that are not part of expected set
    try:
        for f in TEMPLATE_DIR.rglob("*"):
            if f.is_file():
                rel = f.relative_to(TEMPLATE_DIR).as_posix()
                if rel not in expected:
                    try:
                        f.unlink()
                    except Exception:
                        pass
    except Exception:
        pass

    Logger.info(f"Synced {copied} template files into {TEMPLATE_DIR}")
    return copied


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
