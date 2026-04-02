"""
core/utils/cmake_parser.py — Shared CMake file parsing and manipulation utilities.

Consolidates CMake regex patterns previously duplicated across common.py, release.py,
lib.py, sol.py, and create.py into a single authoritative module.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from core.utils.fileops import Transaction

# ── Regex patterns (compiled once) ──────────────────────────────────────────

_RE_PROJECT_VERSION = re.compile(
    r'project\s*\([^)]*VERSION\s+([\d.]+)', re.IGNORECASE | re.DOTALL
)
_RE_PROJECT_NAME = re.compile(
    r'project\s*\(\s*(\S+)', re.IGNORECASE
)
_RE_CMAKE_MIN_VERSION = re.compile(
    r'cmake_minimum_required\s*\(\s*VERSION\s+([\d.]+)', re.IGNORECASE
)
_RE_CXX_STANDARD = re.compile(
    r'(CXX_STANDARD\s+)\d+'
)


# ── Read-only extraction ────────────────────────────────────────────────────

def extract_project_version(cmake_path: Path) -> Optional[str]:
    """Extract VERSION from a project() call in a CMakeLists.txt file.

    Returns the version string or None if not found.
    """
    if not cmake_path.exists():
        return None
    # Strip comments to avoid matching inside comments
    clean = re.sub(r'#.*', '', cmake_path.read_text(encoding="utf-8"))
    m = _RE_PROJECT_VERSION.search(clean)
    return m.group(1) if m else None


def extract_project_name(cmake_path: Path) -> Optional[str]:
    """Extract project name from a project() call.

    Returns the project name or None if not found.
    """
    if not cmake_path.exists():
        return None
    content = cmake_path.read_text(encoding="utf-8")
    m = _RE_PROJECT_NAME.search(content)
    return m.group(1) if m else None


def extract_cmake_minimum_version(cmake_path: Path) -> Optional[str]:
    """Extract VERSION from cmake_minimum_required() call.

    Returns the version string or None if not found.
    """
    if not cmake_path.exists():
        return None
    content = cmake_path.read_text(encoding="utf-8")
    for line in content.splitlines():
        m = _RE_CMAKE_MIN_VERSION.search(line)
        if m:
            return m.group(1)
    return None


# ── Write operations (project-level) ────────────────────────────────────────

def set_project_version(cmake_path: Path, new_version: str) -> bool:
    """Replace the VERSION in project() call. Returns True if changed."""
    if not cmake_path.exists():
        return False
    txt = cmake_path.read_text(encoding="utf-8")
    new_txt, n = re.subn(
        r'(project\([^\n]*VERSION\s+)([0-9.]+)',
        lambda m: m.group(1) + new_version,
        txt,
        flags=re.IGNORECASE,
    )
    if n:
        cmake_path.write_text(new_txt, encoding="utf-8")
        return True
    return False


def set_cmake_minimum_version(
    cmake_path: Path, version: str,
    skip_dirs: tuple[str, ...] = ("external", "build", "_deps", "build-extreme"),
) -> bool:
    """Replace cmake_minimum_required VERSION. Returns True if changed."""
    if not cmake_path.exists():
        return False
    content = cmake_path.read_text(encoding="utf-8")
    new_content = re.sub(
        r'cmake_minimum_required\s*\(\s*VERSION\s+[\d.]+',
        f'cmake_minimum_required(VERSION {version}',
        content,
        flags=re.IGNORECASE,
    )
    if new_content != content:
        cmake_path.write_text(new_content, encoding="utf-8")
        return True
    return False


def set_cxx_standard(cmake_path: Path, std: str) -> bool:
    """Replace CXX_STANDARD value. Returns True if changed."""
    if not cmake_path.exists():
        return False
    content = cmake_path.read_text(encoding="utf-8")
    new_content = _RE_CXX_STANDARD.sub(rf'\g<1>{std}', content)
    if new_content != content:
        cmake_path.write_text(new_content, encoding="utf-8")
        return True
    return False


# ── add_subdirectory manipulation ────────────────────────────────────────────

def _write(path: Path, content: str, txn: Optional["Transaction"] = None) -> None:
    """Write content to file, using Transaction if available."""
    if txn:
        txn.safe_write_text(path, content)
    else:
        path.write_text(content, encoding="utf-8")


def add_subdirectory(
    cmake_path: Path, name: str, txn: Optional["Transaction"] = None,
) -> bool:
    """Append add_subdirectory(name) if not already present. Returns True if added."""
    entry = f"add_subdirectory({name})"

    if cmake_path.exists():
        content = cmake_path.read_text(encoding="utf-8")
        if re.search(
            rf"^\s*add_subdirectory\(\s*{re.escape(name)}\s*\)",
            content, re.MULTILINE,
        ):
            return False  # already present
        new_content = content.rstrip() + f"\n{entry}\n"
        _write(cmake_path, new_content, txn)
    else:
        if not cmake_path.parent.exists():
            if txn:
                txn.safe_mkdir(cmake_path.parent, parents=True, exist_ok=True)
            else:
                cmake_path.parent.mkdir(parents=True, exist_ok=True)
        _write(cmake_path, f"{entry}\n", txn)
    return True


def remove_subdirectory(
    cmake_path: Path, name: str, txn: Optional["Transaction"] = None,
) -> bool:
    """Remove add_subdirectory(name) line. Returns True if removed."""
    if not cmake_path.exists():
        return False
    content = cmake_path.read_text(encoding="utf-8")
    new_content = re.sub(
        rf"^\s*add_subdirectory\(\s*{re.escape(name)}\s*\)\s*\n?",
        "",
        content,
        flags=re.MULTILINE,
    )
    if new_content == content:
        return False
    _write(cmake_path, new_content, txn)
    return True


def rename_subdirectory(
    cmake_path: Path, old: str, new: str, txn: Optional["Transaction"] = None,
) -> bool:
    """Replace add_subdirectory(old) with add_subdirectory(new). Returns True if changed."""
    if not cmake_path.exists():
        return False
    content = cmake_path.read_text(encoding="utf-8")
    new_content = re.sub(
        rf"(add_subdirectory\(\s*){re.escape(old)}(\s*\))",
        rf"\g<1>{new}\2",
        content,
    )
    if new_content == content:
        return False
    _write(cmake_path, new_content, txn)
    return True


# ── target_link_libraries manipulation ──────────────────────────────────────

def update_target_link(
    root: Path, old_target: str, new_target: str,
    txn: Optional["Transaction"] = None,
) -> int:
    """Update target_link_libraries references from old to new across all CMakeLists.txt.

    Returns the number of files changed.
    """
    changed = 0
    for p in root.rglob("CMakeLists.txt"):
        if not p.is_file():
            continue
        content = p.read_text(encoding="utf-8")
        new_content = re.sub(rf"\b{re.escape(old_target)}\b", new_target, content)
        if new_content != content:
            _write(p, new_content, txn)
            changed += 1
    return changed


def remove_target_link(
    root: Path, target: str, txn: Optional["Transaction"] = None,
) -> int:
    """Remove references to target from target_link_libraries.

    Returns the number of files changed.
    """
    changed = 0
    for p in root.rglob("CMakeLists.txt"):
        if not p.is_file():
            continue
        content = p.read_text(encoding="utf-8")
        new_content = re.sub(
            rf"(target_link_libraries\([^)]*)\b{re.escape(target)}\b([^)]*\))",
            lambda m: m.group(1) + m.group(2).replace("  ", " ").strip(),
            content,
        )
        # Cleanup whitespace around parens
        new_content = re.sub(r'\s+\)', ')', new_content)
        new_content = re.sub(r'\(\s+', '(', new_content)
        if new_content != content:
            _write(p, new_content, txn)
            changed += 1
    return changed
