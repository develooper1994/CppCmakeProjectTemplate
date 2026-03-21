#!/usr/bin/env python3
"""
libtool.py — Unified C++ library management tool.

Commands:
    add    <name> [--version] [--namespace] [--deps lib1,lib2] [--link-app] [--dry-run]
    remove <name> [--delete] [--dry-run]
    rename <old> <new> [--dry-run]
    list
    tree
    doctor
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from dataclasses import dataclass, field
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
                "Project root not found (expected libs/, tests/unit/, apps/, scripts/)"
            )
        p = p.parent


PROJECT_ROOT = find_project_root(Path(__file__).resolve())

# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────

VALID_NAME_RE  = re.compile(r"^[a-z][a-z0-9_]*$")
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


def ensure_not_protected(name: str) -> None:
    if name in PROTECTED_LIBS:
        fail(f"'{name}' is protected and cannot be removed or renamed.")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _word_boundary_pattern(token: str) -> re.Pattern:
    return re.compile(rf"(?<![A-Za-z0-9_]){re.escape(token)}(?![A-Za-z0-9_])")


def contains_token(text: str, token: str) -> bool:
    return bool(_word_boundary_pattern(token).search(text))


def replace_token(text: str, old: str, new: str) -> str:
    return _word_boundary_pattern(old).sub(new, text)


def is_under(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


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

    deps_link = ""
    if deps:
        dep_list = "\n".join(f"        {d}" for d in deps)
        deps_link = f"\ntarget_link_libraries({name}\n    PUBLIC\n{dep_list}\n)\n"

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
){deps_link}
if(ENABLE_COVERAGE)     enable_code_coverage({name})         endif()
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
        dep_list = "\n".join(f"- `{d}`" for d in deps)
        deps_section = f"\n## Dependencies\n\n{dep_list}\n"

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

def append_subdirectory(cmake_path: Path, name: str) -> bool:
    if not cmake_path.exists():
        fail(f"Missing CMake file: {cmake_path.relative_to(PROJECT_ROOT)}")
    content = read_text(cmake_path)
    if re.search(
        rf"^\s*add_subdirectory\(\s*{re.escape(name)}\s*\)\s*$",
        content, re.MULTILINE
    ):
        return False
    sep = "\n" if content.endswith("\n") else "\n\n"
    write_text(cmake_path, content + sep + f"add_subdirectory({name})\n")
    return True


def remove_subdirectory(cmake_path: Path, name: str) -> bool:
    if not cmake_path.exists():
        return False
    content = read_text(cmake_path)
    pattern = re.compile(
        rf"^\s*add_subdirectory\(\s*{re.escape(name)}\s*\)\s*\n?", re.MULTILINE
    )
    new_content, count = pattern.subn("", content)
    if count == 0:
        return False
    write_text(cmake_path, new_content)
    return True


def add_link_to_cmake(cmake_path: Path, name: str) -> bool:
    """Adds <name> to the first target_link_libraries PRIVATE block found."""
    if not cmake_path.exists():
        return False
    content = read_text(cmake_path)
    if re.search(rf"^\s+{re.escape(name)}\s*$", content, re.MULTILINE):
        return False  # already present
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


# ──────────────────────────────────────────────────────────────────────────────
# Rename helpers
# ──────────────────────────────────────────────────────────────────────────────

def cxx_text_replace(path: Path, old: str, new: str) -> bool:
    if not path.exists():
        return False
    content = original = read_text(path)

    # Order matters: do specific path/include patterns first
    specific = [
        (f"{old}/{old}.h",          f"{new}/{new}.h"),
        (f"{old}/{old}.hpp",         f"{new}/{new}.hpp"),
        (f"{old}/{old}_export.h",    f"{new}/{new}_export.h"),
        (f"{old}_test.cpp",          f"{new}_test.cpp"),
        (f"{old}.cpp",               f"{new}.cpp"),
        (f"{old}.cc",                f"{new}.cc"),
        (f"{old}.cxx",               f"{new}.cxx"),
        (f"include/{old}",           f"include/{new}"),
        (f"libs/{old}",              f"libs/{new}"),
        (f"tests/unit/{old}",        f"tests/unit/{new}"),
        (f"add_subdirectory({old})", f"add_subdirectory({new})"),
        (f"project({old} ",          f"project({new} "),
        (f"project({old})",          f"project({new})"),
    ]
    for a, b in specific:
        content = content.replace(a, b)

    # Generic word-boundary token replace
    content = replace_token(content, old, new)

    if content == original:
        return False
    write_text(path, content)
    return True


def rename_expected_files(tree_root: Path, old: str, new: str) -> None:
    if not tree_root.exists():
        return

    # include/<old>/ → include/<new>/
    old_inc = tree_root / "include" / old
    new_inc = tree_root / "include" / new
    if old_inc.exists():
        old_inc.rename(new_inc)

    # src/<old>.{cpp,cc,cxx} → src/<new>.*
    src_dir = tree_root / "src"
    if src_dir.exists():
        for ext in ("cpp", "cc", "cxx"):
            f = src_dir / f"{old}.{ext}"
            if f.exists():
                f.rename(src_dir / f"{new}.{ext}")

    # include/<new>/<old>.{h,hpp} → include/<new>/<new>.*
    inc_dir = tree_root / "include" / new
    if inc_dir.exists():
        for ext in ("h", "hpp"):
            f = inc_dir / f"{old}.{ext}"
            if f.exists():
                f.rename(inc_dir / f"{new}.{ext}")

    # <old>_test.cpp → <new>_test.cpp
    old_test = tree_root / f"{old}_test.cpp"
    if old_test.exists():
        old_test.rename(tree_root / f"{new}_test.cpp")


def rewrite_tree(root: Path, old: str, new: str) -> None:
    if not root.exists():
        return
    for file in iter_text_files(root):
        cxx_text_replace(file, old, new)


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
    libs_dir = root / "libs"
    if not libs_dir.exists():
        return []
    return sorted(
        d.name for d in libs_dir.iterdir()
        if d.is_dir() and d.name not in SKIP_DIR_NAMES
    )


def get_lib_deps(name: str, root: Path = PROJECT_ROOT) -> list[str]:
    """Parse target_link_libraries in libs/<name>/CMakeLists.txt."""
    cmake = root / "libs" / name / "CMakeLists.txt"
    if not cmake.exists():
        return []
    content = read_text(cmake)
    # Find PUBLIC/PRIVATE/INTERFACE block for this target
    pattern = re.compile(
        rf"target_link_libraries\(\s*{re.escape(name)}\s*\n"
        rf".*?(?:PUBLIC|PRIVATE|INTERFACE)\s*\n(.*?)\)",
        re.DOTALL,
    )
    m = pattern.search(content)
    if not m:
        return []
    known = set(list_libraries(root))
    deps = []
    for line in m.group(1).splitlines():
        tok = line.strip()
        if tok and tok in known:
            deps.append(tok)
    return deps


# ──────────────────────────────────────────────────────────────────────────────
# Core operations
# ──────────────────────────────────────────────────────────────────────────────

def create_lib_skeleton(
    name: str,
    version: str,
    namespace: str,
    deps: list[str],
    link_app: bool,
    dry_run: bool,
) -> None:
    validate_name(name)

    paths = LibPaths(PROJECT_ROOT, name)
    if paths.lib_dir.exists():
        fail(f"libs/{name} already exists")
    if paths.test_dir.exists():
        fail(f"tests/unit/{name} already exists")

    # Validate deps
    existing = set(list_libraries())
    for dep in deps:
        if dep not in existing:
            fail(f"Dependency '{dep}' not found in libs/. Create it first.")

    if dry_run:
        print(f"[dry-run] create libs/{name}/")
        print(f"[dry-run] create tests/unit/{name}/")
        print(f"[dry-run] add_subdirectory({name}) → libs/CMakeLists.txt")
        print(f"[dry-run] add_subdirectory({name}) → tests/unit/CMakeLists.txt")
        if deps:
            print(f"[dry-run] deps: {', '.join(deps)}")
        if link_app:
            print(f"[dry-run] link → apps/main_app/CMakeLists.txt")
        return

    # Library skeleton
    (paths.lib_dir / "src").mkdir(parents=True)
    (paths.lib_dir / "include" / name).mkdir(parents=True)
    (paths.lib_dir / "docs").mkdir(parents=True)
    write_text(paths.lib_dir / "docs" / ".gitkeep", "")

    write_text(paths.lib_dir / "CMakeLists.txt",
               lib_cmakelists(name, version, namespace, deps))
    write_text(paths.lib_dir / "include" / name / f"{name}.h",
               lib_header(name, namespace))
    write_text(paths.lib_dir / "src" / f"{name}.cpp",
               lib_source(name, namespace))
    write_text(paths.lib_dir / "README.md", lib_readme(name, deps))

    # Test skeleton
    paths.test_dir.mkdir(parents=True)
    write_text(paths.test_dir / "CMakeLists.txt", test_cmakelists(name))
    write_text(paths.test_dir / f"{name}_test.cpp", test_source(name, namespace))

    # CMake registration
    append_subdirectory(paths.libs_cmake, name)
    append_subdirectory(paths.unit_cmake, name)

    print(f"  ✅ libs/{name}/")
    print(f"  ✅ tests/unit/{name}/")

    if deps:
        print(f"  🔗 deps: {', '.join(deps)}")

    if link_app:
        app_cmake = PROJECT_ROOT / "apps" / "main_app" / "CMakeLists.txt"
        if add_link_to_cmake(app_cmake, name):
            print(f"  ✅ linked → apps/main_app/CMakeLists.txt")
        else:
            print(f"  ⏭  apps/main_app already has {name}")


def remove_library(name: str, delete: bool, dry_run: bool) -> None:
    validate_name(name)
    ensure_not_protected(name)

    paths = LibPaths(PROJECT_ROOT, name)
    if not paths.lib_dir.exists():
        fail(f"libs/{name} not found")

    apps_with_link = [
        a for a in iter_app_cmake_files()
        if contains_token(read_text(a), name)
    ]

    if dry_run:
        print("[dry-run]")
        if contains_token(read_text(paths.libs_cmake), name):
            print(f"  - remove add_subdirectory({name}) from libs/CMakeLists.txt")
        if paths.unit_cmake.exists() and contains_token(read_text(paths.unit_cmake), name):
            print(f"  - remove add_subdirectory({name}) from tests/unit/CMakeLists.txt")
        for app in apps_with_link:
            print(f"  - remove {name} link from {app.relative_to(PROJECT_ROOT)}")
        if delete:
            print(f"  - delete libs/{name}/")
            if paths.test_dir.exists():
                print(f"  - delete tests/unit/{name}/")
        return

    remove_subdirectory(paths.libs_cmake, name)
    remove_subdirectory(paths.unit_cmake, name)
    for app in apps_with_link:
        remove_link_from_cmake(app, name)

    if delete:
        dirty = find_references(PROJECT_ROOT, name)
        if dirty:
            fail("References still exist in:\n  - " + "\n  - ".join(dirty))
        if paths.lib_dir.exists():
            shutil.rmtree(paths.lib_dir)
        if paths.test_dir.exists():
            shutil.rmtree(paths.test_dir)
        print(f"  ✅ removed and deleted: {name}")
    else:
        print(f"  ✅ detached (files kept): {name}")


def rename_library(old: str, new: str, dry_run: bool) -> None:
    validate_name(old)
    validate_name(new)
    ensure_not_protected(old)

    old_paths = LibPaths(PROJECT_ROOT, old)
    new_paths = LibPaths(PROJECT_ROOT, new)

    if old == new:
        fail("old and new names are identical")
    if not old_paths.lib_dir.exists():
        fail(f"libs/{old} not found")
    if new_paths.lib_dir.exists():
        fail(f"libs/{new} already exists")

    # Snapshot which apps had the old lib linked BEFORE any changes
    apps_with_old = [
        a for a in iter_app_cmake_files()
        if contains_token(read_text(a), old)
    ]

    if dry_run:
        print("[dry-run]")
        print(f"  - move libs/{old}/ → libs/{new}/")
        if old_paths.test_dir.exists():
            print(f"  - move tests/unit/{old}/ → tests/unit/{new}/")
        print(f"  - rename internal files {old}.* → {new}.*")
        print(f"  - update CMakeLists.txt references")
        for app in apps_with_old:
            print(f"  - re-link {old}→{new} in {app.relative_to(PROJECT_ROOT)}")
        return

    # 1. Move dirs
    shutil.move(str(old_paths.lib_dir), str(new_paths.lib_dir))
    if old_paths.test_dir.exists():
        shutil.move(str(old_paths.test_dir), str(new_paths.test_dir))

    # 2. Rename files inside moved trees
    rename_expected_files(new_paths.lib_dir, old, new)
    rename_expected_files(new_paths.test_dir, old, new)

    # 3. Rewrite moved tree contents
    rewrite_tree(new_paths.lib_dir, old, new)
    rewrite_tree(new_paths.test_dir, old, new)

    # 4. Central CMake: swap add_subdirectory entries
    remove_subdirectory(new_paths.libs_cmake, old)
    append_subdirectory(new_paths.libs_cmake, new)
    remove_subdirectory(new_paths.unit_cmake, old)
    append_subdirectory(new_paths.unit_cmake, new)

    # 5. Re-link apps: remove old, add new (using pre-change snapshot)
    for app in apps_with_old:
        remove_link_from_cmake(app, old)
        add_link_to_cmake(app, new)

    # 6. Sweep remaining project text files
    for file in iter_text_files(PROJECT_ROOT):
        if is_under(file, new_paths.lib_dir) or is_under(file, new_paths.test_dir):
            continue
        if contains_token(read_text(file), old):
            cxx_text_replace(file, old, new)

    print(f"  ✅ renamed: {old} → {new}")


# ──────────────────────────────────────────────────────────────────────────────
# List & Tree
# ──────────────────────────────────────────────────────────────────────────────

def cmd_list(_: argparse.Namespace) -> None:
    names = list_libraries()
    if not names:
        print("No libraries.")
        return
    print("Libraries:")
    for n in names:
        print(f"  {n}")


def cmd_tree(_: argparse.Namespace) -> None:
    """Print ASCII dependency tree for all libraries."""
    names = list_libraries()
    if not names:
        print("No libraries.")
        return

    deps_map: dict[str, list[str]] = {n: get_lib_deps(n) for n in names}

    # Find roots: libs that are not a dependency of anyone else
    all_deps: set[str] = {d for deps in deps_map.values() for d in deps}
    roots = [n for n in names if n not in all_deps]
    if not roots:
        roots = names  # circular or flat — just show all

    visited: set[str] = set()

    def print_node(name: str, prefix: str, is_last: bool) -> None:
        connector = "└── " if is_last else "├── "
        marker = " (cycle)" if name in visited else ""
        print(f"{prefix}{connector}{name}{marker}")
        if name in visited:
            return
        visited.add(name)
        children = deps_map.get(name, [])
        child_prefix = prefix + ("    " if is_last else "│   ")
        for i, child in enumerate(children):
            print_node(child, child_prefix, i == len(children) - 1)

    print("Library dependency tree:")
    for i, root in enumerate(roots):
        print_node(root, "", i == len(roots) - 1)

    # Also show any orphan libs not reachable from roots
    orphans = [n for n in names if n not in visited]
    if orphans:
        print("\nStandalone (no dependents):")
        for n in orphans:
            print(f"  • {n}")


# ──────────────────────────────────────────────────────────────────────────────
# Doctor
# ──────────────────────────────────────────────────────────────────────────────

def cmd_doctor(_: argparse.Namespace) -> None:
    names = list_libraries()
    if not names:
        print("No libraries found.")
        return

    issues = 0
    for name in names:
        test_dir = PROJECT_ROOT / "tests" / "unit" / name
        if not test_dir.exists():
            print(f"  ⚠  Missing test directory: tests/unit/{name}/")
            issues += 1

        readme = PROJECT_ROOT / "libs" / name / "README.md"
        if not readme.exists():
            print(f"  ⚠  Missing README.md: libs/{name}/README.md")
            issues += 1

        refs = find_references(PROJECT_ROOT, name)
        if not refs and name not in PROTECTED_LIBS:
            print(f"  ⚠  Orphan library (no CMake references): {name}")
            issues += 1

        deps = get_lib_deps(name)
        for dep in deps:
            if not (PROJECT_ROOT / "libs" / dep).exists():
                print(f"  ⚠  Broken dependency: {name} → {dep} (not found)")
                issues += 1

    if issues == 0:
        print("  ✅ Project healthy")
    else:
        print(f"\n  {issues} issue(s) found.")
        raise SystemExit(1)


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
    p.add_argument("--namespace", default=None,
                   help="C++ namespace (default: same as name)")
    p.add_argument("--deps",      default="",
                   help="Comma-separated existing libs to depend on (e.g. core,utils)")
    p.add_argument("--link-app",  action="store_true",
                   help="Link to apps/main_app/CMakeLists.txt")
    p.add_argument("--dry-run",   action="store_true")
    p.set_defaults(func=cmd_add)

    # remove
    p = sub.add_parser("remove", help="Detach or delete a library")
    p.add_argument("name")
    p.add_argument("--delete",  action="store_true",
                   help="Also delete libs/<n>/ and tests/unit/<n>/")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_remove)

    # rename
    p = sub.add_parser("rename", help="Rename a library")
    p.add_argument("old")
    p.add_argument("new")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_rename)

    # list
    sub.add_parser("list", help="List all libraries").set_defaults(func=cmd_list)

    # tree
    sub.add_parser("tree", help="Show ASCII dependency tree").set_defaults(func=cmd_tree)

    # doctor
    sub.add_parser("doctor", help="Check project consistency").set_defaults(func=cmd_doctor)

    return parser


# ──────────────────────────────────────────────────────────────────────────────
# Command handlers
# ──────────────────────────────────────────────────────────────────────────────

def cmd_add(args: argparse.Namespace) -> None:
    deps = [d.strip() for d in args.deps.split(",") if d.strip()] if args.deps else []
    ns   = args.namespace or args.name
    validate_name(ns)
    create_lib_skeleton(
        name=args.name,
        version=args.version,
        namespace=ns,
        deps=deps,
        link_app=args.link_app,
        dry_run=args.dry_run,
    )


def cmd_remove(args: argparse.Namespace) -> None:
    remove_library(name=args.name, delete=args.delete, dry_run=args.dry_run)


def cmd_rename(args: argparse.Namespace) -> None:
    rename_library(old=args.old, new=args.new, dry_run=args.dry_run)


def main() -> None:
    build_parser().parse_args().func(build_parser().parse_args())


if __name__ == "__main__":
    args = build_parser().parse_args()
    args.func(args)
