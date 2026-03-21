#!/usr/bin/env python3
"""
lib_manager_core.py — Kütüphane yönetim çekirdek modülü.
"""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

_VALID_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")

PROTECTED_LIBS = {"dummy_lib"}
TEXT_SUFFIXES = {".cpp", ".cc", ".cxx", ".h", ".hpp", ".cmake", ".txt", ".md", ".in"}


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


def validate_name(name: str) -> None:
    if not _VALID_NAME_RE.match(name):
        raise ValueError(
            f"Invalid library name: {name}\n"
            "Must match: [a-z][a-z0-9_]*"
        )


def ensure_not_protected(name: str) -> None:
    if name in PROTECTED_LIBS:
        raise RuntimeError(f"'{name}' is protected")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def list_app_cmake_files(root: Path) -> Iterable[Path]:
    apps_root = root / "apps"
    if not apps_root.exists():
        return []
    return apps_root.rglob("CMakeLists.txt")


def append_subdirectory(cmake: Path, name: str) -> bool:
    if not cmake.exists():
        return False

    content = read_text(cmake)
    line = f"add_subdirectory({name})"

    if re.search(rf"^\s*add_subdirectory\(\s*{re.escape(name)}\s*\)\s*$", content, re.MULTILINE):
        return False

    sep = "\n" if content.endswith("\n") else "\n\n"
    write_text(cmake, content + sep + line + "\n")
    return True


def remove_subdirectory(cmake: Path, name: str) -> bool:
    if not cmake.exists():
        return False

    content = read_text(cmake)
    pattern = re.compile(
        rf"^\s*add_subdirectory\(\s*{re.escape(name)}\s*\)\s*\n?",
        re.MULTILINE,
    )
    new_content, count = pattern.subn("", content)
    if count == 0:
        return False
    write_text(cmake, new_content)
    return True


def add_link_to_target(cmake: Path, name: str) -> bool:
    if not cmake.exists():
        return False

    content = read_text(cmake)

    if re.search(rf"^\s*{re.escape(name)}\s*$", content, re.MULTILINE):
        return False

    pattern = re.compile(r"(target_link_libraries\([^)]*?\bPRIVATE\b\s*\n)", re.MULTILINE)
    new_content, count = pattern.subn(rf"\1        {name}\n", content, count=1)
    if count == 0:
        return False

    write_text(cmake, new_content)
    return True


def remove_link_from_target(cmake: Path, name: str) -> bool:
    if not cmake.exists():
        return False

    content = read_text(cmake)
    pattern = re.compile(rf"^\s+{re.escape(name)}\s*\n?", re.MULTILINE)
    new_content, count = pattern.subn("", content)
    if count == 0:
        return False

    write_text(cmake, new_content)
    return True


def replace_token_in_text(path: Path, old: str, new: str) -> bool:
    if not path.exists():
        return False
    if path.suffix not in TEXT_SUFFIXES and path.name != "CMakeLists.txt":
        return False

    content = read_text(path)

    replacements = [
        (f"{old}/{old}.h", f"{new}/{new}.h"),
        (f"{old}/{old}_export.h", f"{new}/{new}_export.h"),
        (f"{old}/{old}.hpp", f"{new}/{new}.hpp"),
        (f"{old}_test.cpp", f"{new}_test.cpp"),
        (f"{old}.cpp", f"{new}.cpp"),
        (f"{old}.cc", f"{new}.cc"),
        (f"{old}.cxx", f"{new}.cxx"),
        (f"include/{old}", f"include/{new}"),
        (f"libs/{old}", f"libs/{new}"),
        (f"tests/unit/{old}", f"tests/unit/{new}"),
        (f"add_subdirectory({old})", f"add_subdirectory({new})"),
    ]

    new_content = content
    for a, b in replacements:
        new_content = new_content.replace(a, b)

    pattern = re.compile(rf"\b{re.escape(old)}\b")
    new_content = pattern.sub(new, new_content)

    if new_content == content:
        return False

    write_text(path, new_content)
    return True


def _gather_text_files(root: Path) -> Iterable[Path]:
    if not root.exists():
        return []
    return (p for p in root.rglob("*") if p.is_file())


class LibManager:
    def __init__(self, project_root: Path):
        self.root = project_root

    def add(self, name: str) -> None:
        validate_name(name)
        paths = LibPaths(self.root, name)

        append_subdirectory(paths.libs_cmake, name)
        append_subdirectory(paths.unit_cmake, name)

    def remove(self, name: str, delete: bool) -> None:
        validate_name(name)
        ensure_not_protected(name)

        paths = LibPaths(self.root, name)

        remove_subdirectory(paths.libs_cmake, name)
        remove_subdirectory(paths.unit_cmake, name)

        for app in list_app_cmake_files(self.root):
            remove_link_from_target(app, name)

        if delete:
            dirty = self.find_references(name)
            if dirty:
                raise RuntimeError(f"References still exist: {dirty}")

            if paths.lib_dir.exists():
                shutil.rmtree(paths.lib_dir)
            if paths.test_dir.exists():
                shutil.rmtree(paths.test_dir)

    def rename(self, old: str, new: str) -> None:
        validate_name(old)
        validate_name(new)
        ensure_not_protected(old)

        old_paths = LibPaths(self.root, old)
        new_paths = LibPaths(self.root, new)

        if not old_paths.lib_dir.exists():
            raise RuntimeError(f"'{old}' not found")
        if new_paths.lib_dir.exists():
            raise RuntimeError(f"'{new}' already exists")

        # 1) Klasörleri taşı
        shutil.move(str(old_paths.lib_dir), str(new_paths.lib_dir))
        if old_paths.test_dir.exists():
            shutil.move(str(old_paths.test_dir), str(new_paths.test_dir))

        # 2) Dosya adlarını değiştir
        self._rename_expected_files(new_paths.lib_dir, old, new)
        self._rename_expected_files(new_paths.test_dir, old, new)

        # 3) İçerik referanslarını güncelle
        self._rewrite_tree(new_paths.lib_dir, old, new)
        self._rewrite_tree(new_paths.test_dir, old, new)

        # 4) CMake referanslarını güncelle
        remove_subdirectory(new_paths.libs_cmake, old)
        append_subdirectory(new_paths.libs_cmake, new)

        remove_subdirectory(new_paths.unit_cmake, old)
        append_subdirectory(new_paths.unit_cmake, new)

        for app in list_app_cmake_files(self.root):
            remove_link_from_target(app, old)
            add_link_to_target(app, new)

        # 5) Root altındaki diğer metin dosyaları da güncellenecekse:
        for file in _gather_text_files(self.root):
            if file.is_relative_to(new_paths.lib_dir) or file.is_relative_to(new_paths.test_dir):
                continue
            replace_token_in_text(file, old, new)

    def find_references(self, name: str) -> list[str]:
        dirty: list[str] = []
        check_files = [
            self.root / "libs" / "CMakeLists.txt",
            self.root / "tests" / "unit" / "CMakeLists.txt",
            *list_app_cmake_files(self.root),
        ]
        for f in check_files:
            if f.exists() and name in read_text(f):
                dirty.append(str(f.relative_to(self.root)))
        return dirty

    def _rewrite_tree(self, root: Path, old: str, new: str) -> None:
        if not root.exists():
            return
        for file in _gather_text_files(root):
            replace_token_in_text(file, old, new)

    def _rename_expected_files(self, root: Path, old: str, new: str) -> None:
        if not root.exists():
            return

        candidates = [
            root / "src" / f"{old}.cpp",
            root / "include" / old / f"{old}.h",
            root / "include" / old / f"{old}.hpp",
            root / f"{old}_test.cpp",
            root / "README.md",
            root / "CMakeLists.txt",
        ]

        for path in candidates:
            if not path.exists():
                continue

        # include/<old> -> include/<new>
        old_inc = root / "include" / old
        new_inc = root / "include" / new
        if old_inc.exists():
            old_inc.rename(new_inc)

        # src/<old>.cpp -> src/<new>.cpp
        old_cpp = root / "src" / f"{old}.cpp"
        if old_cpp.exists():
            old_cpp.rename(root / "src" / f"{new}.cpp")

        old_cc = root / "src" / f"{old}.cc"
        if old_cc.exists():
            old_cc.rename(root / "src" / f"{new}.cc")

        old_cxx = root / "src" / f"{old}.cxx"
        if old_cxx.exists():
            old_cxx.rename(root / "src" / f"{new}.cxx")

        # header
        old_h = root / "include" / new / f"{old}.h"
        if old_h.exists():
            old_h.rename(root / "include" / new / f"{new}.h")

        old_hpp = root / "include" / new / f"{old}.hpp"
        if old_hpp.exists():
            old_hpp.rename(root / "include" / new / f"{new}.hpp")

        # test
        old_test = root / f"{old}_test.cpp"
        if old_test.exists():
            old_test.rename(root / f"{new}_test.cpp")
