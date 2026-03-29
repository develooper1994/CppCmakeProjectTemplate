from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import List, Optional

from .paths import paths_for, validate_name
from .templates import (
    lib_cmakelists,
    lib_cmakelists_header_only,
    lib_header,
    lib_source,
    lib_header_singleton,
    lib_source_singleton,
    lib_header_pimpl,
    lib_source_pimpl,
    lib_header_factory,
    lib_source_factory,
    lib_header_observer,
    lib_source_observer,
)
from .tokens import apply_template_dir
from core.utils.fileops import Transaction

try:
    from .jinja_helpers import render_template_file as _render_template_file
    _USE_JINJA_CREATE = True
except Exception:
    _render_template_file = None
    _USE_JINJA_CREATE = False


PROTECTED_LIBS = {"dummy_lib"}


# ── CMakeLists helpers ────────────────────────────────────────────────────────

def _cmake_add_subdirectory(cmake_path: Path, name: str) -> bool:
    """Append add_subdirectory(name) if not already present. Returns True if added."""
    entry = f"add_subdirectory({name})"
    # Optional transactional write: callers may pass a Transaction via kwargs
    txn = None
    # inspect caller locals for a Transaction (conservative; common call sites pass txn parameter)
    try:
        import inspect
        frame = inspect.currentframe().f_back
        if frame is not None and "txn" in frame.f_locals:
            txn = frame.f_locals.get("txn")
    except Exception:
        txn = None

    if cmake_path.exists():
        content = cmake_path.read_text(encoding="utf-8")
        if re.search(rf"^\s*add_subdirectory\(\s*{re.escape(name)}\s*\)", content, re.MULTILINE):
            return False  # already present
        new_content = content.rstrip() + f"\n{entry}\n"
        if txn:
            txn.safe_write_text(cmake_path, new_content)
        else:
            cmake_path.write_text(new_content, encoding="utf-8")
    else:
        if cmake_path.parent.exists() is False:
            if txn:
                txn.safe_mkdir(cmake_path.parent, parents=True, exist_ok=True)
            else:
                cmake_path.parent.mkdir(parents=True, exist_ok=True)
        if txn:
            txn.safe_write_text(cmake_path, f"{entry}\n")
        else:
            cmake_path.write_text(f"{entry}\n", encoding="utf-8")
    return True


def _cmake_remove_subdirectory(cmake_path: Path, name: str) -> bool:
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
    cmake_path.write_text(new_content, encoding="utf-8")
    return True


def _cmake_rename_subdirectory(cmake_path: Path, old: str, new: str) -> bool:
    """Replace add_subdirectory(old) with add_subdirectory(new)."""
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
    cmake_path.write_text(new_content, encoding="utf-8")
    return True


def _replace_tokens_in_tree(root: Path, old: str, new: str) -> None:
    """Replace all occurrences of old→new in text files under root."""
    TEXT_SUFFIXES = {".cpp", ".cc", ".cxx", ".h", ".hpp", ".cmake", ".txt", ".md", ".in"}
    for p in root.rglob("*"):
        if p.is_file() and (p.suffix in TEXT_SUFFIXES or p.name == "CMakeLists.txt"):
            try:
                content = p.read_text(encoding="utf-8", errors="replace")
                if old in content:
                    p.write_text(content.replace(old, new), encoding="utf-8")
            except Exception:
                pass


# ── Public API ─────────────────────────────────────────────────────────────────

def create_library(
    name: str,
    version: str = "1.0.0",
    namespace: Optional[str] = None,
    deps: Optional[List[str]] = None,
    header_only: bool = False,
    interface: bool = False,
    template: str = "",
    cxx_standard: str = "",
    link_app: bool = False,
    dry_run: bool = False,
    root: Optional[Path] = None,
) -> None:
    deps = deps or []
    validate_name(name)
    p = paths_for(name, root)
    project_root = Path(root) if root is not None else Path(__file__).resolve().parents[4]

    libs_cmake  = project_root / "libs" / "CMakeLists.txt"
    tests_cmake = project_root / "tests" / "unit" / "CMakeLists.txt"

    # External template dir (e.g. from Jinja/extension templates)
    if template and template not in ("singleton", "pimpl", "observer", "factory"):
        template_dir = project_root / "extension" / "templates" / "libs" / template
        if template_dir.exists() and template_dir.is_dir():
            if dry_run:
                print(f"[dry-run] create libs/{name}/ from template '{template}'")
                return
            apply_template_dir(template_dir, p.lib_dir, name, dry_run=False)
            _cmake_add_subdirectory(libs_cmake, name)
            print(f"✅ libs/{name}/ created from template '{template}'")
            return

    if p.lib_dir.exists():
        raise FileExistsError(f"Library '{name}' already exists")

    if dry_run:
        print(f"[dry-run] create libs/{name}/")
        print(f"[dry-run] create tests/unit/{name}/")
        print("[dry-run] register in libs/CMakeLists.txt")
        print("[dry-run] register in tests/unit/CMakeLists.txt")
        return

    # ── Create directory structure ─────────────────────────────────────────
    p.lib_dir.mkdir(parents=True, exist_ok=False)
    if not interface:
        p.include_subdir.mkdir(parents=True)
    if not (header_only or interface):
        p.src_dir.mkdir(parents=True)

    # ── Write files ───────────────────────────────────────────────────────
    ns = namespace or name
    if header_only or interface:
        p.cmake.write_text(
            lib_cmakelists_header_only(name, version, ns, deps, cxx_standard),
            encoding="utf-8",
        )
        if not interface:
            p.header_file.write_text(lib_header(name, ns), encoding="utf-8")
    else:
        _tmpl = template or ""
        if _tmpl == "singleton":
            p.header_file.write_text(lib_header_singleton(name, ns), encoding="utf-8")
            p.source_file.write_text(lib_source_singleton(name, ns), encoding="utf-8")
        elif _tmpl == "pimpl":
            p.header_file.write_text(lib_header_pimpl(name, ns), encoding="utf-8")
            p.source_file.write_text(lib_source_pimpl(name, ns), encoding="utf-8")
        elif _tmpl == "factory":
            p.header_file.write_text(lib_header_factory(name, ns), encoding="utf-8")
            p.source_file.write_text(lib_source_factory(name, ns), encoding="utf-8")
        elif _tmpl == "observer":
            p.header_file.write_text(lib_header_observer(name, ns), encoding="utf-8")
            p.source_file.write_text(lib_source_observer(name, ns), encoding="utf-8")
        else:
            p.header_file.write_text(lib_header(name, ns), encoding="utf-8")
            p.source_file.write_text(lib_source(name, ns), encoding="utf-8")
        p.cmake.write_text(
            lib_cmakelists(name, version, ns, deps, cxx_standard),
            encoding="utf-8",
        )

    if _USE_JINJA_CREATE:
        p.readme.write_text(_render_template_file("readme.jinja2", name=name), encoding="utf-8")
    else:
        p.readme.write_text(f"# {name}\n\nGenerated library: {name}\n", encoding="utf-8")

    # ── Tests ──────────────────────────────────────────────────────────────
    if not interface:
        p.tests_dir.mkdir(parents=True, exist_ok=True)
        tests_cmake_lib = p.tests_dir / "CMakeLists.txt"
        if _USE_JINJA_CREATE:
            tests_cmake_lib.write_text(_render_template_file("tests_cmake.jinja2", name=name), encoding="utf-8")
            (p.tests_dir / f"{name}_test.cpp").write_text(_render_template_file("test_cpp.jinja2", name=name), encoding="utf-8")
        else:
            tests_cmake_lib.write_text(
                f"add_executable({name}_tests {name}_test.cpp)\n"
                f"target_link_libraries({name}_tests PRIVATE {name} GTest::gtest_main)\n"
                f"add_test(NAME {name}_tests COMMAND {name}_tests)\n",
                encoding="utf-8",
            )
            (p.tests_dir / f"{name}_test.cpp").write_text(
                f"#include <gtest/gtest.h>\n\n"
                f"TEST({name}_Test, Placeholder) {{ EXPECT_TRUE(true); }}\n",
                encoding="utf-8",
            )

    # ── Register in CMakeLists.txt files (always) ─────────────────────────
    _cmake_add_subdirectory(libs_cmake, name)
    if not interface:
        _cmake_add_subdirectory(tests_cmake, name)

    print(f"✅ libs/{name}/")
    if not interface:
        print(f"✅ tests/unit/{name}/")
    print("✅ Registered in libs/CMakeLists.txt")
    if not interface:
        print("✅ Registered in tests/unit/CMakeLists.txt")
    if deps:
        print(f"🔗 deps: {', '.join(deps)}")


def remove_library(name: str, delete: bool = False, dry_run: bool = False, root: Optional[Path] = None) -> None:
    if name in PROTECTED_LIBS:
        raise ValueError(f"'{name}' is a protected library and cannot be removed")
    validate_name(name)
    p = paths_for(name, root)
    project_root = Path(root) if root is not None else Path(__file__).resolve().parents[4]

    libs_cmake  = project_root / "libs" / "CMakeLists.txt"
    tests_cmake = project_root / "tests" / "unit" / "CMakeLists.txt"

    if not p.lib_dir.exists():
        raise FileNotFoundError(f"Library '{name}' not found")

    if dry_run:
        print(f"[dry-run] unregister {name} from libs/CMakeLists.txt")
        print(f"[dry-run] unregister {name} from tests/unit/CMakeLists.txt")
        if delete:
            print(f"[dry-run] delete libs/{name}/")
            print(f"[dry-run] delete tests/unit/{name}/")
        return

    _cmake_remove_subdirectory(libs_cmake, name)
    _cmake_remove_subdirectory(tests_cmake, name)

    if delete:
        if p.lib_dir.exists():
            shutil.rmtree(p.lib_dir)
        if p.tests_dir.exists():
            shutil.rmtree(p.tests_dir)
        print(f"✅ Deleted: libs/{name}/ and tests/unit/{name}/")
    else:
        print(f"✅ Detached: {name} (files kept, CMake entries removed)")


def rename_library(old: str, new: str, dry_run: bool = False, root: Optional[Path] = None) -> None:
    if old in PROTECTED_LIBS:
        raise ValueError(f"'{old}' is protected and cannot be renamed")
    validate_name(old)
    validate_name(new)
    p_old = paths_for(old, root)
    p_new = paths_for(new, root)
    project_root = Path(root) if root is not None else Path(__file__).resolve().parents[4]

    if not p_old.lib_dir.exists():
        raise FileNotFoundError(f"Library '{old}' not found")
    if p_new.lib_dir.exists():
        raise FileExistsError(f"Library '{new}' already exists")

    libs_cmake  = project_root / "libs" / "CMakeLists.txt"
    tests_cmake = project_root / "tests" / "unit" / "CMakeLists.txt"

    if dry_run:
        print(f"[dry-run] rename libs/{old} → libs/{new}")
        print(f"[dry-run] rename tests/unit/{old} → tests/unit/{new}")
        print("[dry-run] update CMake references")
        return

    # Move directories
    p_old.lib_dir.rename(p_new.lib_dir)
    if p_old.tests_dir.exists():
        p_old.tests_dir.rename(p_new.tests_dir)

    # Update all token references within moved dirs
    _replace_tokens_in_tree(p_new.lib_dir, old, new)
    if p_new.tests_dir.exists():
        _replace_tokens_in_tree(p_new.tests_dir, old, new)

    # Update CMakeLists.txt registrations
    _cmake_rename_subdirectory(libs_cmake, old, new)
    _cmake_rename_subdirectory(tests_cmake, old, new)

    print(f"✅ Renamed: {old} → {new}")


def move_library(name: str, dest: str, dry_run: bool = False, root: Optional[Path] = None) -> None:
    """Move library to a new subdirectory path within libs/ (e.g. 'graphics/renderer')."""
    validate_name(name)
    p = paths_for(name, root)
    project_root = Path(root) if root is not None else Path(__file__).resolve().parents[4]

    if not p.lib_dir.exists():
        raise FileNotFoundError(f"Library '{name}' not found")

    new_dir = project_root / "libs" / dest
    if new_dir.exists():
        raise FileExistsError(f"Destination '{dest}' already exists")

    libs_cmake = project_root / "libs" / "CMakeLists.txt"

    if dry_run:
        print(f"[dry-run] move libs/{name} → libs/{dest}")
        return

    new_dir.parent.mkdir(parents=True, exist_ok=True)
    p.lib_dir.rename(new_dir)
    _cmake_remove_subdirectory(libs_cmake, name)
    # Re-register with new relative path
    _cmake_add_subdirectory(libs_cmake, dest)
    print(f"✅ Moved: libs/{name} → libs/{dest}")
