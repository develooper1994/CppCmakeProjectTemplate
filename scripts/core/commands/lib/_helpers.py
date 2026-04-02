"""Shared constants and helpers for lib subcommands."""
from __future__ import annotations

import re

from core.utils.common import PROJECT_ROOT

LIBS_DIR = PROJECT_ROOT / "libs"


def _ensure_libs() -> None:
    LIBS_DIR.mkdir(exist_ok=True)


def _get_lib_deps(name: str) -> list[str]:
    """Parse CMakeLists.txt to find target_link_libraries."""
    cm = LIBS_DIR / name / "CMakeLists.txt"
    if not cm.exists():
        return []
    content = cm.read_text(encoding="utf-8")
    match = re.search(
        r'target_link_libraries\(\s*\w+\s+(?:PUBLIC|PRIVATE|INTERFACE)\s+([^)]+)\)',
        content,
        re.DOTALL,
    )
    if not match:
        return []
    raw_deps = match.group(1).split()
    return [d for d in raw_deps if d not in ("PUBLIC", "PRIVATE", "INTERFACE") and d.strip()]
