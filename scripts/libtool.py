#!/usr/bin/env python3
"""
libtool.py — Unified C++ library management tool.

Commands:
    add    <name> [--version V] [--namespace NS] [--deps a,b] [--link-app] [--dry-run]
    remove <name> [--delete] [--dry-run]
    rename <old> <new> [--dry-run]
    move   <name> <dest> [--dry-run]      # dest = new_name OR subdir/new_name
    deps   <name> (--add a,b | --remove a,b) [--dry-run]
    list
    tree
    doctor

Examples:
    libtool.py add core
    libtool.py add renderer --deps core,math --link-app
    libtool.py move renderer graphics/renderer
    libtool.py deps renderer --add math --remove old_dep
    libtool.py rename my_lib better_lib
    libtool.py remove old_lib --delete
    libtool.py tree
    libtool.py doctor
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

# ──────────────────────────────────────────────────────────────────────────────
# Project root detection
# ──────────────────────────────────────────────────────────────────────────────

def find_project_root(start: Path) -> Path:
    p = start.resolve()
    if p.is_file():
        p = p.parent
    while True:
        if (
            (p / "libs").is_dir()
            and (p / "tests" / "unit").is_dir()
            and (p / "apps").is_dir()
            and (p / "scripts").is_dir()
        ):
            return p
        if p.parent == p:
            raise RuntimeError(
                "Project root not found. Expected libs/, tests/unit/, apps/, scripts/."
            )
        p = p.parent


PROJECT_ROOT = find_project_root(Path(__file__).resolve())

# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────

VALID_NAME_RE  = re.compile(r"^[a-z][a-z0-9_]*$")
VALID_PATH_RE  = re.compile(r"^[a-z][a-z0-9_/]*$")   # allows subdir/name
PROTECTED_LIBS = {"dummy_lib"}

TEXT_SUFFIXES = {
    ".cpp", ".cc", ".cxx", ".h", ".hpp",
    ".cmake", ".txt", ".md", ".in",
    ".json", ".yml", ".yaml", ".toml",
}

SKIP_DIR_NAMES = {
    ".git", ".idea", ".vscode", "__pycache__",
    "build", "cmake-build-debug", "cmake-build-release", "out",
}

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def fail(msg: str, code: int = 1) -> "NoReturn":
    print(f"❌  {msg}", file=sys.stderr)
    raise SystemExit(code)


def validate_name(name: str) -> None:
    if not VALID_NAME_RE.match(name):
        fail(f"Invalid library name '{name}'. Must match [a-z][a-z0-9_]*")


def validate_path(dest: str) -> None:
    if not VALID_PATH_RE.match(dest):
        fail(f"Invalid destination '{dest}'. Use lowercase letters, digits, underscores and forward slashes.")


def ensure_not_protected(name: str) -> None:
    if name in PROTECTED_LIBS:
        fail(f"'{name}' is protected and cannot be modified.")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _word_re(token: str) -> re.Pattern:
    return re.compile(rf"(?<![A-Za-z0-9_]){re.escape(token)}(?![A-Za-z0-9_])")


def contains_token(text: str, token: str) -> bool:
    return bool(_word_re(token).search(text))


def replace_token(text: str, old: str, new: str) -> str:
    return _word_re(old).sub(new, text)


def is_under(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def parse_deps_arg(raw: str) -> list[str]:
    return [d.strip() for d in raw.split(",") if d.strip()] if raw else []


# ──────────────────────────────────────────────────────────────────────────────
# LibPaths — path helpers for a library
# ──────────────────────────────────────────────────────────────────────────────

@dataclass(slots=True)
class LibPaths:
    """
    Paths for a library identified by its leaf name.
    dest_path is relative to libs/ and may contain subdirs (e.g. "network/http").
    """
    root:      Path
    leaf_name: str
    dest_path: str = ""   # relative to libs/, e.g. "utils/math" or just "math"

    def __post_init__(self) -> None:
        if not self.dest_path:
            self.dest_path = self.leaf_name

    @property
    def lib_dir(self) -> Path:
        return self.root / "libs" / self.dest_path

    @property
    def test_dir(self) -> Path:
        return self.root / "tests" / "unit" / self.leaf_name

    @property
    def libs_cmake(self) -> Path:
        return self.root / "libs" / "CMakeLists.txt"

    @property
    def unit_cmake(self) -> Path:
        return self.root / "tests" / "unit" / "CMakeLists.txt"

    @property
    def cmake_subdir_arg(self) -> str:
        """The argument passed to add_subdirectory() in libs/CMakeLists.txt."""
        return self.dest_path


def paths_for(name: str, root: Path = PROJECT_ROOT) -> LibPaths:
    """Look up the actual dest_path of an existing lib by leaf name."""
    lib_dir = root / "libs" / name
    if lib_dir.exists():
        return LibPaths(root, name, name)
    # Search one level deep for subdirectory layouts (e.g. libs/graphics/renderer)
    for candidate in (root / "libs").rglob("CMakeLists.txt"):
        if candidate.parent.name == name:
            rel = candidate.parent.relative_to(root / "libs")
            return LibPaths(root, name, str(rel).replace("\\", "/"))
    return LibPaths(root, name, name)


# ──────────────────────────────────────────────────────────────────────────────
# File iteration
# ──────────────────────────────────────────────────────────────────────────────

def iter_app_cmake_files(root: Path = PROJECT_ROOT) -> list[Path]:
    apps_root = root / "apps"
    if not apps_root.exists():
        return []
    return [p for p in apps_root.rglob("CMakeLists.txt") if p.is_file()]


def iter_text_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIR_NAMES for part in path.parts):
            continue
        if path.suffix.lower() in TEXT_SUFFIXES or path.name == "CMakeLists.txt":
            yield path


# ──────────────────────────────────────────────────────────────────────────────
# Templates
# ──────────────────────────────────────────────────────────────────────────────

def lib_cmakelists(name: str, version: str, namespace: str, deps: list[str]) -> str:
    upper = name.upper()
    deps_block = ""
    if deps:
        dep_lines = "\n".join(f"        {d}" for d in deps)
        deps_block = f"\ntarget_link_libraries({name}\n    PUBLIC\n{dep_lines}\n)\n"

    return f"""\
# libs/{name}/CMakeLists.txt

if(CMAKE_SOURCE_DIR STREQUAL CMAKE_CURRENT_SOURCE_DIR)
    cmake_minimum_required(VERSION 3.25)
    project({name} VERSION {version} LANGUAGES CXX)
    list(APPEND CMAKE_MODULE_PATH "${{CMAKE_CURRENT_SOURCE_DIR}}/../../cmake")
    include(ProjectConfigs OPTIONAL)
    include(ProjectOptions OPTIONAL)
    include(Sanitizers OPTIONAL)
endif()

include(GenerateExportHeader)

add_library({name})

target_generate_build_info({name}
    NAMESPACE {namespace}
    PROJECT_VERSION "{version}"
)

target_sources({name}
    PRIVATE src/{name}.cpp
    PUBLIC FILE_SET HEADERS BASE_DIRS include
           FILES include/{name}/{name}.h
)

generate_export_header({name}
    BASE_NAME {upper}
    EXPORT_FILE_NAME "${{CMAKE_CURRENT_BINARY_DIR}}/generated/{name}/{name}_export.h"
)

target_include_directories({name} PUBLIC
    $<BUILD_INTERFACE:${{CMAKE_CURRENT_SOURCE_DIR}}/include>
    $<BUILD_INTERFACE:${{CMAKE_CURRENT_BINARY_DIR}}/generated>
    $<INSTALL_INTERFACE:include>
)

set_target_properties({name} PROPERTIES
    CXX_VISIBILITY_PRESET hidden
    VISIBILITY_INLINES_HIDDEN 1
){deps_block}
if(ENABLE_COVERAGE)          enable_code_coverage({name})     endif()
if(COMMAND enable_sanitizers)    enable_sanitizers({name})    endif()
if(COMMAND set_project_warnings) set_project_warnings({name}) endif()

install(TARGETS {name} EXPORT {name}_Targets FILE_SET HEADERS)
"""


def lib_header(name: str, namespace: str) -> str:
    upper = name.upper()
    return f"""\
#pragma once

#include <string>
#include "{name}/{name}_export.h"

namespace {namespace} {{

{upper}_EXPORT std::string get_info();

}} // namespace {namespace}
"""


def lib_source(name: str, namespace: str) -> str:
    return f"""\
#include "{name}/{name}.h"

namespace {namespace} {{

std::string get_info()
{{
    return "Hello from {name}!";
}}

}} // namespace {namespace}
"""


def lib_readme(name: str, deps: list[str]) -> str:
    deps_section = ""
    if deps:
        dep_lines = "\n".join(f"- `{d}`" for d in deps)
        deps_section = f"\n## Dependencies\n\n{dep_lines}\n"
    return f"""\
# {name}

TODO: Bu kütüphanenin ne yaptığını açıkla.
{deps_section}
## Kullanım

```cpp
#include <{name}/{name}.h>

auto info = {name}::get_info();
```
"""


def test_cmakelists(name: str) -> str:
    return f"""\
add_executable({name}_tests {name}_test.cpp)

target_link_libraries({name}_tests
    PRIVATE
        {name}
        GTest::gtest_main
)

set_project_warnings({name}_tests)

add_test(NAME {name}_tests COMMAND {name}_tests)
"""


def test_source(name: str, namespace: str) -> str:
    return f"""\
#include <gtest/gtest.h>
#include "{name}/{name}.h"

TEST({name}_Test, GetInfoReturnsNonEmptyString)
{{
    EXPECT_FALSE({namespace}::get_info().empty());
}}

TEST({name}_Test, GetInfoContainsLibName)
{{
    EXPECT_NE({namespace}::get_info().find("{name}"), std::string::npos);
}}
"""


# ──────────────────────────────────────────────────────────────────────────────
# CMake manipulation
# ──────────────────────────────────────────────────────────────────────────────

def append_subdirectory(cmake_path: Path, subdir: str) -> bool:
    """Add add_subdirectory(<subdir>) if not already present."""
    if not cmake_path.exists():
        fail(f"Missing: {cmake_path}")
    content = read_text(cmake_path)
    escaped = re.escape(subdir)
    if re.search(rf"^\s*add_subdirectory\(\s*{escaped}\s*\)\s*$", content, re.MULTILINE):
        return False
    sep = "\n" if content.endswith("\n") else "\n\n"
    write_text(cmake_path, content + sep + f"add_subdirectory({subdir})\n")
    return True


def remove_subdirectory(cmake_path: Path, subdir: str) -> bool:
    if not cmake_path.exists():
        return False
    content = read_text(cmake_path)
    pattern = re.compile(
        rf"^\s*add_subdirectory\(\s*{re.escape(subdir)}\s*\)\s*\n?", re.MULTILINE
    )
    new_content, count = pattern.subn("", content)
    if count == 0:
        return False
    write_text(cmake_path, new_content)
    return True


def add_link_to_cmake(cmake_path: Path, name: str) -> bool:
    """Insert <name> into the first target_link_libraries PRIVATE block."""
    if not cmake_path.exists():
        return False
    content = read_text(cmake_path)
    if re.search(rf"^\s+{re.escape(name)}\s*$", content, re.MULTILINE):
        return False
    pattern = re.compile(
        r"(target_link_libraries\(\s*\w+\b.*?\bPRIVATE\b\s*\n)",
        re.DOTALL | re.MULTILINE,
    )
    new_content, count = pattern.subn(rf"\1        {name}\n", content, count=1)
    if count == 0:
        return False
    write_text(cmake_path, new_content)
    return True


def remove_link_from_cmake(cmake_path: Path, name: str) -> bool:
    if not cmake_path.exists():
        return False
    content = read_text(cmake_path)
    pattern = re.compile(rf"^\s+{re.escape(name)}\s*(#.*)?\n?", re.MULTILINE)
    new_content, count = pattern.subn("", content)
    if count == 0:
        return False
    write_text(cmake_path, new_content)
    return True


def edit_lib_deps(lib_cmake: Path, lib_name: str, add: list[str], remove: list[str]) -> None:
    """
    Modify the target_link_libraries PUBLIC block of a library's CMakeLists.txt.
    Creates the block if it doesn't exist and deps are being added.
    """
    if not lib_cmake.exists():
        fail(f"Not found: {lib_cmake}")

    content = read_text(lib_cmake)

    # Pattern: target_link_libraries(<lib_name>\n    PUBLIC\n<lines>\n)
    block_re = re.compile(
        rf"(target_link_libraries\(\s*{re.escape(lib_name)}\s*\n\s*PUBLIC\s*\n)(.*?)(\))",
        re.DOTALL,
    )
    m = block_re.search(content)

    if m:
        # Parse existing dep lines
        lines = [l.strip() for l in m.group(2).splitlines() if l.strip()]
        for dep in remove:
            if dep in lines:
                lines.remove(dep)
            else:
                print(f"  ⚠  '{dep}' not in deps of {lib_name}, skipped")
        for dep in add:
            if dep not in lines:
                lines.append(dep)
        if lines:
            new_body = "\n".join(f"        {l}" for l in lines) + "\n"
            new_block = m.group(1) + new_body + m.group(3)
        else:
            # Remove the whole block
            new_block = ""
        content = content[:m.start()] + new_block + content[m.end():]

    elif add:
        # No block exists — create one before the first if(ENABLE_COVERAGE) line
        dep_lines = "\n".join(f"        {d}" for d in add)
        new_block = (
            f"\ntarget_link_libraries({lib_name}\n"
            f"    PUBLIC\n{dep_lines}\n)\n"
        )
        # Insert before quality guards
        insert_re = re.compile(r"^(if\(ENABLE_COVERAGE\))", re.MULTILINE)
        im = insert_re.search(content)
        if im:
            content = content[:im.start()] + new_block + content[im.start():]
        else:
            content += new_block

    write_text(lib_cmake, content)


# ──────────────────────────────────────────────────────────────────────────────
# Rename / rewrite helpers
# ──────────────────────────────────────────────────────────────────────────────

def cxx_text_replace(path: Path, old: str, new: str) -> bool:
    if not path.exists():
        return False
    content = original = read_text(path)
    specific = [
        (f"{old}/{old}.h",           f"{new}/{new}.h"),
        (f"{old}/{old}.hpp",          f"{new}/{new}.hpp"),
        (f"{old}/{old}_export.h",     f"{new}/{new}_export.h"),
        (f"{old}_test.cpp",           f"{new}_test.cpp"),
        (f"{old}.cpp",                f"{new}.cpp"),
        (f"{old}.cc",                 f"{new}.cc"),
        (f"{old}.cxx",                f"{new}.cxx"),
        (f"include/{old}",            f"include/{new}"),
        (f"libs/{old}",               f"libs/{new}"),
        (f"tests/unit/{old}",         f"tests/unit/{new}"),
        (f"add_subdirectory({old})",  f"add_subdirectory({new})"),
        (f"project({old} ",           f"project({new} "),
        (f"project({old})",           f"project({new})"),
    ]
    for a, b in specific:
        content = content.replace(a, b)
    content = replace_token(content, old, new)
    if content == original:
        return False
    write_text(path, content)
    return True


def rename_files_in_tree(tree_root: Path, old: str, new: str) -> None:
    if not tree_root.exists():
        return
    for src, ext in [
        (tree_root / "include" / old,            None),          # directory
        (tree_root / "src" / f"{old}.cpp",       f"{new}.cpp"),
        (tree_root / "src" / f"{old}.cc",        f"{new}.cc"),
        (tree_root / "src" / f"{old}.cxx",       f"{new}.cxx"),
        (tree_root / f"{old}_test.cpp",           f"{new}_test.cpp"),
    ]:
        if src.exists():
            dst = src.parent / (ext if ext else new)
            src.rename(dst)
    # header inside include/<new>/
    inc_dir = tree_root / "include" / new
    if inc_dir.exists():
        for h_ext in ("h", "hpp"):
            f = inc_dir / f"{old}.{h_ext}"
            if f.exists():
                f.rename(inc_dir / f"{new}.{h_ext}")


def rewrite_tree(root: Path, old: str, new: str) -> None:
    if not root.exists():
        return
    for f in iter_text_files(root):
        cxx_text_replace(f, old, new)


# ──────────────────────────────────────────────────────────────────────────────
# Project scanning
# ──────────────────────────────────────────────────────────────────────────────

def find_references(root: Path, name: str) -> list[str]:
    check_files = [
        root / "libs" / "CMakeLists.txt",
        root / "tests" / "unit" / "CMakeLists.txt",
        *iter_app_cmake_files(root),
    ]
    return [
        str(f.relative_to(root))
        for f in check_files
        if f.exists() and contains_token(read_text(f), name)
    ]


def list_libraries(root: Path = PROJECT_ROOT) -> list[str]:
    """Return sorted list of leaf library names (handles subdirectory layouts)."""
    libs_dir = root / "libs"
    if not libs_dir.exists():
        return []
    names = []
    for p in libs_dir.rglob("CMakeLists.txt"):
        if p.parent == libs_dir:
            continue  # skip the top-level libs/CMakeLists.txt
        if p.parent.parent == libs_dir or p.parent.parent.parent == libs_dir:
            name = p.parent.name
            if name not in SKIP_DIR_NAMES and name not in names:
                names.append(name)
    return sorted(names)


def get_lib_deps(name: str, root: Path = PROJECT_ROOT) -> list[str]:
    cmake = paths_for(name, root).lib_dir / "CMakeLists.txt"
    if not cmake.exists():
        return []
    content = read_text(cmake)
    pattern = re.compile(
        rf"target_link_libraries\(\s*{re.escape(name)}\s*\n\s*(?:PUBLIC|PRIVATE|INTERFACE)\s*\n(.*?)\)",
        re.DOTALL,
    )
    m = pattern.search(content)
    if not m:
        return []
    known = set(list_libraries(root))
    return [l.strip() for l in m.group(1).splitlines() if l.strip() and l.strip() in known]


# ──────────────────────────────────────────────────────────────────────────────
# Core operations
# ──────────────────────────────────────────────────────────────────────────────

def create_lib_skeleton(
    name: str, version: str, namespace: str,
    deps: list[str], link_app: bool, dry_run: bool,
) -> None:
    validate_name(name)
    p = LibPaths(PROJECT_ROOT, name)

    if p.lib_dir.exists():
        fail(f"libs/{name} already exists")
    if p.test_dir.exists():
        fail(f"tests/unit/{name} already exists")

    existing = set(list_libraries())
    for dep in deps:
        if dep not in existing:
            fail(f"Dependency '{dep}' not found in libs/. Create it first.")

    if dry_run:
        print(f"[dry-run] create libs/{name}/")
        print(f"[dry-run] create tests/unit/{name}/")
        print(f"[dry-run] add_subdirectory({name}) → libs/CMakeLists.txt")
        print(f"[dry-run] add_subdirectory({name}) → tests/unit/CMakeLists.txt")
        if deps:    print(f"[dry-run] deps: {', '.join(deps)}")
        if link_app: print(f"[dry-run] link → apps/main_app/CMakeLists.txt")
        return

    (p.lib_dir / "src").mkdir(parents=True)
    (p.lib_dir / "include" / name).mkdir(parents=True)
    (p.lib_dir / "docs").mkdir(parents=True)
    write_text(p.lib_dir / "docs" / ".gitkeep", "")
    write_text(p.lib_dir / "CMakeLists.txt",        lib_cmakelists(name, version, namespace, deps))
    write_text(p.lib_dir / "include" / name / f"{name}.h", lib_header(name, namespace))
    write_text(p.lib_dir / "src" / f"{name}.cpp",   lib_source(name, namespace))
    write_text(p.lib_dir / "README.md",              lib_readme(name, deps))

    p.test_dir.mkdir(parents=True)
    write_text(p.test_dir / "CMakeLists.txt",        test_cmakelists(name))
    write_text(p.test_dir / f"{name}_test.cpp",      test_source(name, namespace))

    append_subdirectory(p.libs_cmake, name)
    append_subdirectory(p.unit_cmake, name)

    print(f"  ✅ libs/{name}/")
    print(f"  ✅ tests/unit/{name}/")
    if deps:
        print(f"  🔗 deps: {', '.join(deps)}")
    if link_app:
        app_cmake = PROJECT_ROOT / "apps" / "main_app" / "CMakeLists.txt"
        ok = add_link_to_cmake(app_cmake, name)
        print(f"  {'✅' if ok else '⏭ '} linked → apps/main_app/CMakeLists.txt")


def remove_library(name: str, delete: bool, dry_run: bool) -> None:
    validate_name(name)
    ensure_not_protected(name)

    p = paths_for(name)
    if not p.lib_dir.exists():
        fail(f"libs/{name} not found")

    apps_with_link = [a for a in iter_app_cmake_files() if contains_token(read_text(a), name)]

    if dry_run:
        print("[dry-run]")
        if contains_token(read_text(p.libs_cmake), p.cmake_subdir_arg):
            print(f"  - remove add_subdirectory({p.cmake_subdir_arg}) from libs/CMakeLists.txt")
        if p.unit_cmake.exists() and contains_token(read_text(p.unit_cmake), name):
            print(f"  - remove add_subdirectory({name}) from tests/unit/CMakeLists.txt")
        for app in apps_with_link:
            print(f"  - remove {name} link from {app.relative_to(PROJECT_ROOT)}")
        if delete:
            print(f"  - delete libs/{p.cmake_subdir_arg}/")
            if p.test_dir.exists():
                print(f"  - delete tests/unit/{name}/")
        return

    remove_subdirectory(p.libs_cmake, p.cmake_subdir_arg)
    remove_subdirectory(p.unit_cmake, name)
    for app in apps_with_link:
        remove_link_from_cmake(app, name)

    if delete:
        dirty = find_references(PROJECT_ROOT, name)
        if dirty:
            fail("References still exist in:\n  - " + "\n  - ".join(dirty))
        if p.lib_dir.exists():  shutil.rmtree(p.lib_dir)
        if p.test_dir.exists(): shutil.rmtree(p.test_dir)
        print(f"  ✅ removed and deleted: {name}")
    else:
        print(f"  ✅ detached (files kept): {name}")


def rename_library(old: str, new: str, dry_run: bool) -> None:
    validate_name(old)
    validate_name(new)
    ensure_not_protected(old)

    op = paths_for(old)
    np = LibPaths(PROJECT_ROOT, new)

    if old == new:              fail("Names are identical")
    if not op.lib_dir.exists(): fail(f"libs/{old} not found")
    if np.lib_dir.exists():     fail(f"libs/{new} already exists")

    apps_snapshot = [a for a in iter_app_cmake_files() if contains_token(read_text(a), old)]

    if dry_run:
        print("[dry-run]")
        print(f"  - move libs/{op.cmake_subdir_arg}/ → libs/{new}/")
        if op.test_dir.exists(): print(f"  - move tests/unit/{old}/ → tests/unit/{new}/")
        print(f"  - rename internal files {old}.* → {new}.*")
        print(f"  - update CMakeLists.txt references")
        for app in apps_snapshot:
            print(f"  - re-link {old}→{new} in {app.relative_to(PROJECT_ROOT)}")
        return

    shutil.move(str(op.lib_dir), str(np.lib_dir))
    if op.test_dir.exists():
        shutil.move(str(op.test_dir), str(np.test_dir))

    rename_files_in_tree(np.lib_dir,  old, new)
    rename_files_in_tree(np.test_dir, old, new)
    rewrite_tree(np.lib_dir,  old, new)
    rewrite_tree(np.test_dir, old, new)

    remove_subdirectory(np.libs_cmake, op.cmake_subdir_arg)
    append_subdirectory(np.libs_cmake, new)
    remove_subdirectory(np.unit_cmake, old)
    append_subdirectory(np.unit_cmake, new)

    for app in apps_snapshot:
        remove_link_from_cmake(app, old)
        add_link_to_cmake(app, new)

    for f in iter_text_files(PROJECT_ROOT):
        if is_under(f, np.lib_dir) or is_under(f, np.test_dir):
            continue
        if contains_token(read_text(f), old):
            cxx_text_replace(f, old, new)

    print(f"  ✅ renamed: {old} → {new}")


def move_library(name: str, dest: str, dry_run: bool) -> None:
    """
    Move a library to a new location within libs/.
    dest can be a simple name (equivalent to rename) or a path like 'graphics/renderer'.
    The leaf name of dest becomes the new library name.
    """
    validate_name(name)
    validate_path(dest)
    ensure_not_protected(name)

    new_leaf = dest.split("/")[-1]
    validate_name(new_leaf)

    op = paths_for(name)
    np = LibPaths(PROJECT_ROOT, new_leaf, dest)

    if not op.lib_dir.exists():
        fail(f"libs/{name} not found")
    if np.lib_dir.exists():
        fail(f"libs/{dest} already exists")

    apps_snapshot = [a for a in iter_app_cmake_files() if contains_token(read_text(a), name)]

    if dry_run:
        print("[dry-run]")
        print(f"  - move libs/{op.cmake_subdir_arg}/ → libs/{dest}/")
        if op.test_dir.exists():
            print(f"  - move tests/unit/{name}/ → tests/unit/{new_leaf}/")
        if name != new_leaf:
            print(f"  - rename internal files {name}.* → {new_leaf}.*")
        print(f"  - update add_subdirectory: '{op.cmake_subdir_arg}' → '{dest}'")
        for app in apps_snapshot:
            print(f"  - re-link {name}→{new_leaf} in {app.relative_to(PROJECT_ROOT)}")
        return

    # Move directories
    np.lib_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(op.lib_dir), str(np.lib_dir))

    new_test_dir = PROJECT_ROOT / "tests" / "unit" / new_leaf
    if op.test_dir.exists():
        shutil.move(str(op.test_dir), str(new_test_dir))

    # Rename files if leaf name changed
    if name != new_leaf:
        rename_files_in_tree(np.lib_dir,  name, new_leaf)
        rename_files_in_tree(new_test_dir, name, new_leaf)
        rewrite_tree(np.lib_dir,  name, new_leaf)
        rewrite_tree(new_test_dir, name, new_leaf)

    # Update central CMake
    remove_subdirectory(np.libs_cmake, op.cmake_subdir_arg)
    append_subdirectory(np.libs_cmake, dest)

    remove_subdirectory(np.unit_cmake, name)
    if new_leaf != name:
        append_subdirectory(np.unit_cmake, new_leaf)
    else:
        append_subdirectory(np.unit_cmake, name)

    # Re-link apps
    for app in apps_snapshot:
        remove_link_from_cmake(app, name)
        if new_leaf != name:
            add_link_to_cmake(app, new_leaf)
        else:
            add_link_to_cmake(app, name)

    # Sweep remaining text files
    if name != new_leaf:
        for f in iter_text_files(PROJECT_ROOT):
            if is_under(f, np.lib_dir) or is_under(f, new_test_dir):
                continue
            if contains_token(read_text(f), name):
                cxx_text_replace(f, name, new_leaf)

    print(f"  ✅ moved: libs/{name} → libs/{dest}")


def modify_deps(name: str, add: list[str], remove: list[str], dry_run: bool) -> None:
    """Add or remove library dependencies from an existing library."""
    validate_name(name)
    p = paths_for(name)

    if not p.lib_dir.exists():
        fail(f"libs/{name} not found")

    existing = set(list_libraries())
    for dep in add:
        if dep not in existing:
            fail(f"Dependency '{dep}' not found in libs/. Create it first.")
        if dep == name:
            fail(f"A library cannot depend on itself.")

    lib_cmake = p.lib_dir / "CMakeLists.txt"

    if dry_run:
        current = get_lib_deps(name)
        after_remove = [d for d in current if d not in remove]
        after_add    = after_remove + [d for d in add if d not in after_remove]
        print(f"[dry-run] {name} deps:")
        print(f"  before : {current or '(none)'}")
        print(f"  after  : {after_add or '(none)'}")
        return

    edit_lib_deps(lib_cmake, name, add, remove)
    current = get_lib_deps(name)
    print(f"  ✅ {name} deps updated: {current or '(none)'}")


# ──────────────────────────────────────────────────────────────────────────────
# list / tree / doctor
# ──────────────────────────────────────────────────────────────────────────────

def cmd_list(_: argparse.Namespace) -> None:
    names = list_libraries()
    if not names:
        print("No libraries.")
        return
    print("Libraries:")
    for n in names:
        p = paths_for(n)
        suffix = f"  ({p.cmake_subdir_arg})" if p.cmake_subdir_arg != n else ""
        print(f"  {n}{suffix}")


def cmd_tree(_: argparse.Namespace) -> None:
    names = list_libraries()
    if not names:
        print("No libraries.")
        return

    deps_map: dict[str, list[str]] = {n: get_lib_deps(n) for n in names}
    all_deps: set[str]             = {d for ds in deps_map.values() for d in ds}
    roots                          = [n for n in names if n not in all_deps] or names
    visited: set[str]              = set()

    def node(name: str, prefix: str, last: bool) -> None:
        conn   = "└── " if last else "├── "
        cycle  = " (cycle)" if name in visited else ""
        print(f"{prefix}{conn}{name}{cycle}")
        if name in visited:
            return
        visited.add(name)
        children     = deps_map.get(name, [])
        child_prefix = prefix + ("    " if last else "│   ")
        for i, child in enumerate(children):
            node(child, child_prefix, i == len(children) - 1)

    print("Library dependency tree:")
    for i, r in enumerate(roots):
        node(r, "", i == len(roots) - 1)

    orphans = [n for n in names if n not in visited]
    if orphans:
        print("\nStandalone (no dependents):")
        for n in orphans:
            print(f"  • {n}")


def cmd_doctor(_: argparse.Namespace) -> None:
    names  = list_libraries()
    issues = 0

    if not names:
        print("No libraries found.")
        return

    for name in names:
        p = paths_for(name)

        if not (PROJECT_ROOT / "tests" / "unit" / name).exists():
            print(f"  ⚠  Missing test dir: tests/unit/{name}/")
            issues += 1

        if not (p.lib_dir / "README.md").exists():
            print(f"  ⚠  Missing README: libs/{p.cmake_subdir_arg}/README.md")
            issues += 1

        refs = find_references(PROJECT_ROOT, name)
        if not refs and name not in PROTECTED_LIBS:
            print(f"  ⚠  Orphan library (no CMake references): {name}")
            issues += 1

        for dep in get_lib_deps(name):
            if not paths_for(dep).lib_dir.exists():
                print(f"  ⚠  Broken dependency: {name} → {dep}")
                issues += 1

    if issues == 0:
        print("  ✅ Project healthy")
    else:
        print(f"\n  {issues} issue(s) found.")
        raise SystemExit(1)


# ──────────────────────────────────────────────────────────────────────────────
# Command handlers
# ──────────────────────────────────────────────────────────────────────────────

def cmd_add(args: argparse.Namespace) -> None:
    create_lib_skeleton(
        name      = args.name,
        version   = args.version,
        namespace = args.namespace or args.name,
        deps      = parse_deps_arg(args.deps),
        link_app  = args.link_app,
        dry_run   = args.dry_run,
    )


def cmd_remove(args: argparse.Namespace) -> None:
    remove_library(name=args.name, delete=args.delete, dry_run=args.dry_run)


def cmd_rename(args: argparse.Namespace) -> None:
    rename_library(old=args.old, new=args.new, dry_run=args.dry_run)


def cmd_move(args: argparse.Namespace) -> None:
    move_library(name=args.name, dest=args.dest, dry_run=args.dry_run)


def cmd_deps(args: argparse.Namespace) -> None:
    add    = parse_deps_arg(getattr(args, "add",    ""))
    remove = parse_deps_arg(getattr(args, "remove", ""))
    if not add and not remove:
        fail("Specify --add and/or --remove")
    modify_deps(name=args.name, add=add, remove=remove, dry_run=args.dry_run)


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="libtool.py",
        description="Unified C++ library management tool",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # add
    p = sub.add_parser("add", help="Create a new library skeleton")
    p.add_argument("name")
    p.add_argument("--version",   default="1.0.0")
    p.add_argument("--namespace", default=None)
    p.add_argument("--deps",      default="", help="Comma-separated deps, e.g. core,math")
    p.add_argument("--link-app",  action="store_true")
    p.add_argument("--dry-run",   action="store_true")
    p.set_defaults(func=cmd_add)

    # remove
    p = sub.add_parser("remove", help="Detach or delete a library")
    p.add_argument("name")
    p.add_argument("--delete",  action="store_true", help="Also delete files")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_remove)

    # rename
    p = sub.add_parser("rename", help="Rename a library (updates all references)")
    p.add_argument("old")
    p.add_argument("new")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_rename)

    # move
    p = sub.add_parser("move",
        help="Move library to new location (supports subdirs: graphics/renderer)")
    p.add_argument("name",  help="Current library name")
    p.add_argument("dest",  help="Destination path (e.g. new_name or subdir/new_name)")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_move)

    # deps
    p = sub.add_parser("deps", help="Add or remove dependencies of an existing library")
    p.add_argument("name")
    p.add_argument("--add",    default="", help="Comma-separated deps to add")
    p.add_argument("--remove", default="", help="Comma-separated deps to remove")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_deps)

    # list
    sub.add_parser("list",   help="List all libraries").set_defaults(func=cmd_list)

    # tree
    sub.add_parser("tree",   help="ASCII dependency tree").set_defaults(func=cmd_tree)

    # doctor
    sub.add_parser("doctor", help="Check project consistency").set_defaults(func=cmd_doctor)

    return parser


def main() -> None:
    parser = build_parser()
    args   = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
