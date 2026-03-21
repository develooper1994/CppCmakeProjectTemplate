#!/usr/bin/env python3
"""
lib_manager_core.py — Kütüphane yönetimi çekirdek modülü.

Tek sorumluluk:
    - filesystem işlemleri
    - CMake referans yönetimi
    - doğrulama
    - rename atomik operasyonu

CLI içermez.

--- Example usage ---
from lib_manager_core import LibManager

mgr = LibManager(Path.cwd())

mgr.add("math_utils")

mgr.remove(
    "math_utils",
    delete=True,
)

mgr.rename(
    "math_utils",
    "math_core",
)
"""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


# ──────────────────────────────────────────────────────────────────────────────
# Config / State
# ──────────────────────────────────────────────────────────────────────────────

_VALID_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")

PROTECTED_LIBS = {
    "dummy_lib",
}


@dataclass(slots=True)
class LibPaths:
    root: Path
    name: str

    @property
    def lib_dir(self) -> Path:
        return self.root / "libs" / self.name

    @property
    def test_dir(self) -> Path:
        return self.root / "tests" / "unit" / self.name

    @property
    def libs_cmake(self) -> Path:
        return self.root / "libs" / "CMakeLists.txt"

    @property
    def unit_cmake(self) -> Path:
        return self.root / "tests" / "unit" / "CMakeLists.txt"

    @property
    def apps_root(self) -> Path:
        return self.root / "apps"


# ──────────────────────────────────────────────────────────────────────────────
# Validation
# ──────────────────────────────────────────────────────────────────────────────

def validate_name(name: str) -> None:
    if not _VALID_NAME_RE.match(name):
        raise ValueError(
            f"Invalid library name: {name}\n"
            "Must match: [a-z][a-z0-9_]*"
        )


def ensure_not_protected(name: str) -> None:
    if name in PROTECTED_LIBS:
        raise RuntimeError(f"{name} is protected")


# ──────────────────────────────────────────────────────────────────────────────
# File helpers
# ──────────────────────────────────────────────────────────────────────────────

def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def safe_replace_file(path: Path, pattern: re.Pattern, repl: str) -> bool:
    if not path.exists():
        return False

    content = read_text(path)

    new_content, count = pattern.subn(repl, content)

    if count == 0:
        return False

    write_text(path, new_content)
    return True


def list_app_cmake_files(root: Path) -> Iterable[Path]:
    return (root / "apps").rglob("CMakeLists.txt")


# ──────────────────────────────────────────────────────────────────────────────
# CMake operations
# ──────────────────────────────────────────────────────────────────────────────

def append_subdirectory(cmake: Path, name: str) -> bool:

    line = f"add_subdirectory({name})"

    content = read_text(cmake)

    if line in content:
        return False

    sep = "\n" if content.endswith("\n") else "\n\n"

    write_text(
        cmake,
        content + sep + line + "\n",
    )

    return True


def remove_subdirectory(cmake: Path, name: str) -> bool:

    pattern = re.compile(
        rf"^\s*add_subdirectory\(\s*{re.escape(name)}\s*\)\s*\n?",
        re.MULTILINE,
    )

    return safe_replace_file(
        cmake,
        pattern,
        "",
    )


def add_link_to_target(cmake: Path, name: str) -> bool:

    if not cmake.exists():
        return False

    content = read_text(cmake)

    if name in content:
        return False

    pattern = re.compile(
        r"(target_link_libraries\([^)]*PRIVATE\s*\n)",
        re.MULTILINE,
    )

    new_content, count = pattern.subn(
        rf"\1        {name}\n",
        content,
        count=1,
    )

    if count == 0:
        return False

    write_text(cmake, new_content)

    return True


def remove_link_from_target(cmake: Path, name: str) -> bool:

    pattern = re.compile(
        rf"^\s+{re.escape(name)}\s*\n",
        re.MULTILINE,
    )

    return safe_replace_file(
        cmake,
        pattern,
        "",
    )


# ──────────────────────────────────────────────────────────────────────────────
# Reference scan
# ──────────────────────────────────────────────────────────────────────────────

def find_references(root: Path, name: str) -> list[str]:

    dirty: list[str] = []

    files = [
        root / "libs" / "CMakeLists.txt",
        root / "tests" / "unit" / "CMakeLists.txt",
        *list_app_cmake_files(root),
    ]

    for f in files:

        if not f.exists():
            continue

        if name in read_text(f):
            dirty.append(str(f.relative_to(root)))

    return dirty


# ──────────────────────────────────────────────────────────────────────────────
# Filesystem operations
# ──────────────────────────────────────────────────────────────────────────────

def delete_directory(path: Path) -> None:

    if path.exists():
        shutil.rmtree(path)


def move_directory(src: Path, dst: Path) -> None:

    shutil.move(
        str(src),
        str(dst),
    )


# ──────────────────────────────────────────────────────────────────────────────
# Rename logic
# ──────────────────────────────────────────────────────────────────────────────

def rename_files_inside(
    root: Path,
    old: str,
    new: str,
) -> None:

    patterns = [
        (f"{old}.cpp", f"{new}.cpp"),
        (f"{old}.h", f"{new}.h"),
        (f"{old}_test.cpp", f"{new}_test.cpp"),
    ]

    for path in root.rglob("*"):

        if not path.is_file():
            continue

        for old_name, new_name in patterns:

            if path.name == old_name:

                path.rename(
                    path.with_name(new_name)
                )


def replace_content_inside(
    root: Path,
    old: str,
    new: str,
) -> None:

    pattern = re.compile(
        rf"\b{re.escape(old)}\b"
    )

    for file in root.rglob("*"):

        if not file.is_file():
            continue

        if file.suffix not in {
            ".cpp",
            ".h",
            ".cmake",
            ".txt",
            ".md",
        }:
            continue

        safe_replace_file(
            file,
            pattern,
            new,
        )


# ──────────────────────────────────────────────────────────────────────────────
# Public operations
# ──────────────────────────────────────────────────────────────────────────────

class LibManager:

    def __init__(self, project_root: Path):

        self.root = project_root

    # ─────────────────────────────────────────

    def add(
        self,
        name: str,
    ) -> None:

        validate_name(name)

        paths = LibPaths(
            self.root,
            name,
        )

        append_subdirectory(
            paths.libs_cmake,
            name,
        )

        append_subdirectory(
            paths.unit_cmake,
            name,
        )

    # ─────────────────────────────────────────

    def remove(
        self,
        name: str,
        delete: bool,
    ) -> None:

        validate_name(name)

        ensure_not_protected(name)

        paths = LibPaths(
            self.root,
            name,
        )

        remove_subdirectory(
            paths.libs_cmake,
            name,
        )

        remove_subdirectory(
            paths.unit_cmake,
            name,
        )

        for app in list_app_cmake_files(self.root):

            remove_link_from_target(
                app,
                name,
            )

        if delete:

            dirty = find_references(
                self.root,
                name,
            )

            if dirty:

                raise RuntimeError(
                    f"References still exist: {dirty}"
                )

            delete_directory(
                paths.lib_dir,
            )

            delete_directory(
                paths.test_dir,
            )

    # ─────────────────────────────────────────

    def rename(
        self,
        old: str,
        new: str,
    ) -> None:

        validate_name(old)
        validate_name(new)

        ensure_not_protected(old)

        old_paths = LibPaths(
            self.root,
            old,
        )

        new_paths = LibPaths(
            self.root,
            new,
        )

        if not old_paths.lib_dir.exists():

            raise RuntimeError(
                f"{old} not found"
            )

        if new_paths.lib_dir.exists():

            raise RuntimeError(
                f"{new} already exists"
            )

        # move directories

        move_directory(
            old_paths.lib_dir,
            new_paths.lib_dir,
        )

        if old_paths.test_dir.exists():

            move_directory(
                old_paths.test_dir,
                new_paths.test_dir,
            )

        # rename files

        rename_files_inside(
            new_paths.lib_dir,
            old,
            new,
        )

        rename_files_inside(
            new_paths.test_dir,
            old,
            new,
        )

        # replace content

        replace_content_inside(
            new_paths.lib_dir,
            old,
            new,
        )

        replace_content_inside(
            new_paths.test_dir,
            old,
            new,
        )

        # update CMake references

        remove_subdirectory(
            new_paths.libs_cmake,
            old,
        )

        append_subdirectory(
            new_paths.libs_cmake,
            new,
        )

        remove_subdirectory(
            new_paths.unit_cmake,
            old,
        )

        append_subdirectory(
            new_paths.unit_cmake,
            new,
        )

        for app in list_app_cmake_files(self.root):

            remove_link_from_target(
                app,
                old,
            )

            add_link_to_target(
                app,
                new,
            )
