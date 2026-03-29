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
from core.utils.common import Logger

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
    # Check for Transaction in caller context
    txn = None
    try:
        import inspect
        frame = inspect.currentframe().f_back
        if frame is not None and "txn" in frame.f_locals:
            txn = frame.f_locals.get("txn")
    except Exception:
        pass

    if txn:
        txn.safe_write_text(cmake_path, new_content)
    else:
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

    txn = None
    try:
        import inspect
        frame = inspect.currentframe().f_back
        if frame is not None and "txn" in frame.f_locals:
            txn = frame.f_locals.get("txn")
    except Exception:
        pass

    if txn:
        txn.safe_write_text(cmake_path, new_content)
    else:
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


def _update_cmake_references(old: str, new: str, root: Path, txn: Optional[Transaction] = None) -> None:
    """Update target_link_libraries references from 'old' to 'new' in all CMakeLists.txt."""
    for p in root.rglob("CMakeLists.txt"):
        if p.is_file():
            content = p.read_text(encoding="utf-8")
            # Match target_link_libraries and replace the dependency
            new_content = re.sub(rf"\b{re.escape(old)}\b", new, content)
            if new_content != content:
                if txn:
                    txn.safe_write_text(p, new_content)
                else:
                    p.write_text(new_content, encoding="utf-8")


def _remove_cmake_references(target: str, root: Path, txn: Optional[Transaction] = None) -> None:
    """Remove references to 'target' from all target_link_libraries in CMakeLists.txt."""
    for p in root.rglob("CMakeLists.txt"):
        if p.is_file():
            content = p.read_text(encoding="utf-8")
            # Remove the target from target_link_libraries
            new_content = re.sub(rf"(target_link_libraries\([^)]*)\b{re.escape(target)}\b([^)]*\))",
                                 lambda m: m.group(1) + m.group(2).replace("  ", " ").strip(),
                                 content)
            # Cleanup double spaces or spaces before closing parenthesis
            new_content = re.sub(r'\s+\)', ')', new_content)
            new_content = re.sub(r'\(\s+', '(', new_content)

            if new_content != content:
                if txn:
                    txn.safe_write_text(p, new_content)
                else:
                    p.write_text(new_content, encoding="utf-8")


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

    ns = namespace or name
    with Transaction(project_root) as txn:
        txn.safe_mkdir(p.lib_dir, parents=True, exist_ok=False)
        if not interface:
            txn.safe_mkdir(p.include_subdir, parents=True, exist_ok=True)
        if not (header_only or interface):
            txn.safe_mkdir(p.src_dir, parents=True, exist_ok=True)

        if header_only or interface:
            txn.safe_write_text(p.cmake, lib_cmakelists_header_only(name, version, ns, deps, cxx_standard))
            if not interface:
                txn.safe_write_text(p.header_file, lib_header(name, ns))
        else:
            _tmpl = template or ""
            if _tmpl == "singleton":
                txn.safe_write_text(p.header_file, lib_header_singleton(name, ns))
                txn.safe_write_text(p.source_file, lib_source_singleton(name, ns))
            elif _tmpl == "pimpl":
                txn.safe_write_text(p.header_file, lib_header_pimpl(name, ns))
                txn.safe_write_text(p.source_file, lib_source_pimpl(name, ns))
            elif _tmpl == "factory":
                txn.safe_write_text(p.header_file, lib_header_factory(name, ns))
                txn.safe_write_text(p.source_file, lib_source_factory(name, ns))
            elif _tmpl == "observer":
                txn.safe_write_text(p.header_file, lib_header_observer(name, ns))
                txn.safe_write_text(p.source_file, lib_source_observer(name, ns))
            else:
                txn.safe_write_text(p.header_file, lib_header(name, ns))
                txn.safe_write_text(p.source_file, lib_source(name, ns))
            txn.safe_write_text(p.cmake, lib_cmakelists(name, version, ns, deps, cxx_standard))

        if _USE_JINJA_CREATE:
            txn.safe_write_text(p.readme, _render_template_file("readme.jinja2", name=name))
        else:
            txn.safe_write_text(p.readme, f"# {name}\n\nGenerated library: {name}\n")

        if not interface:
            txn.safe_mkdir(p.tests_dir, parents=True, exist_ok=True)
            tests_cmake_lib = p.tests_dir / "CMakeLists.txt"
            if _USE_JINJA_CREATE:
                txn.safe_write_text(tests_cmake_lib, _render_template_file("tests_cmake.jinja2", name=name))
                txn.safe_write_text(p.tests_dir / f"{name}_test.cpp", _render_template_file("test_cpp.jinja2", name=name))
            else:
                txn.safe_write_text(tests_cmake_lib, (
                    f"add_executable({name}_tests {name}_test.cpp)\n"
                    f"target_link_libraries({name}_tests PRIVATE {name} GTest::gtest_main)\n"
                    f"add_test(NAME {name}_tests COMMAND {name}_tests)\n"
                ))
                txn.safe_write_text(p.tests_dir / f"{name}_test.cpp",
                    f"#include <gtest/gtest.h>\n\nTEST({name}_Test, Placeholder) {{ EXPECT_TRUE(true); }}\n")

        _cmake_add_subdirectory(libs_cmake, name)
        if not interface:
            _cmake_add_subdirectory(tests_cmake, name)

    print(f"✅ libs/{name}/")
    if not interface: print(f"✅ tests/unit/{name}/")
    print("✅ Registered in libs/CMakeLists.txt")
    if not interface: print("✅ Registered in tests/unit/CMakeLists.txt")
    if deps: print(f"🔗 deps: {', '.join(deps)}")


def remove_library(name: str, delete: bool = False, dry_run: bool = False, root: Optional[Path] = None) -> None:
    if name in PROTECTED_LIBS:
        raise ValueError(f"'{name}' is a protected library and cannot be removed")
    validate_name(name)
    p = paths_for(name, root)
    project_root = Path(root) if root is not None else Path(__file__).resolve().parents[4]

    libs_cmake  = project_root / "libs" / "CMakeLists.txt"
    tests_cmake = project_root / "tests" / "unit" / "CMakeLists.txt"
    # Resolve actual lib/tests locations. Support moved libraries (e.g. libs/sub/name).
    actual_lib_dir = p.lib_dir
    actual_tests_dir = p.tests_dir
    cmake_entry = name

    # If lib dir is missing, try to locate it under libs/ recursively.
    libs_root = project_root / "libs"
    if not actual_lib_dir.exists() and libs_root.exists():
        candidates = [d for d in libs_root.rglob(name) if d.is_dir()]
        if candidates:
            # prefer the shallowest candidate (fewest path parts)
            candidates.sort(key=lambda d: len(d.relative_to(libs_root).parts))
            candidate = candidates[0]
            actual_lib_dir = candidate
            rel = candidate.relative_to(libs_root)
            cmake_entry = rel.as_posix()
            actual_tests_dir = project_root / "tests" / "unit" / rel
            Logger.debug(f"remove_library: resolved moved lib '{name}' -> {actual_lib_dir}")

    # We allow removal even if lib_dir is missing, to cleanup tests/unit or CMake entries
    exists = actual_lib_dir.exists() or actual_tests_dir.exists()

    if not exists and not delete:
        # Check if it exists in CMake at least (allow either plain name or moved path)
        in_libs = False
        if libs_cmake.exists():
            content = libs_cmake.read_text(encoding="utf-8")
            if re.search(rf"^\s*add_subdirectory\(\s*{re.escape(name)}\s*\)", content, re.MULTILINE) or \
               re.search(rf"^\s*add_subdirectory\(\s*{re.escape(cmake_entry)}\s*\)", content, re.MULTILINE):
                in_libs = True
        if not in_libs:
            raise FileNotFoundError(f"Library '{name}' not found in filesystem or CMakeLists.txt")

    if dry_run:
        print(f"[dry-run] unregister {cmake_entry} from libs/CMakeLists.txt")
        print(f"[dry-run] unregister {cmake_entry} from tests/unit/CMakeLists.txt")
        if delete:
            if actual_lib_dir.exists(): print(f"[dry-run] delete {actual_lib_dir.relative_to(project_root).as_posix()}/")
            if actual_tests_dir.exists(): print(f"[dry-run] delete {actual_tests_dir.relative_to(project_root).as_posix()}/")
        return

    with Transaction(project_root) as txn:
        _cmake_remove_subdirectory(libs_cmake, cmake_entry)
        _cmake_remove_subdirectory(tests_cmake, cmake_entry)
        _remove_cmake_references(name, project_root, txn)

        if delete:
            # remove actual library and tests directories (where present)
            if actual_lib_dir.exists(): txn.safe_remove(actual_lib_dir)
            if actual_tests_dir.exists(): txn.safe_remove(actual_tests_dir)

            # prune empty parent directories under libs/ and tests/unit/
            try:
                # prune libs parents
                parent = actual_lib_dir.parent
                stop = libs_root
                while parent.exists() and parent != stop and parent != project_root:
                    try:
                        if any(parent.iterdir()):
                            break
                    except Exception:
                        break
                    Logger.debug(f"remove_library: pruning empty parent {parent}")
                    txn.safe_remove(parent)
                    parent = parent.parent
            except Exception:
                pass

            try:
                # prune tests parents
                tests_root = project_root / "tests" / "unit"
                parent = actual_tests_dir.parent
                stop = tests_root
                while parent.exists() and parent != stop and parent != project_root:
                    try:
                        if any(parent.iterdir()):
                            break
                    except Exception:
                        break
                    Logger.debug(f"remove_library: pruning empty parent {parent}")
                    txn.safe_remove(parent)
                    parent = parent.parent
            except Exception:
                pass

            print(f"✅ Deleted files for {name}")
        else:
            print(f"✅ Detached {name} (CMake entries removed)")


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

    with Transaction(project_root) as txn:
        txn.safe_rename(p_old.lib_dir, p_new.lib_dir)
        if p_old.tests_dir.exists():
            txn.safe_rename(p_old.tests_dir, p_new.tests_dir)

        _replace_tokens_in_tree(p_new.lib_dir, old, new)
        if p_new.tests_dir.exists():
            _replace_tokens_in_tree(p_new.tests_dir, old, new)

        _cmake_rename_subdirectory(libs_cmake, old, new)
        _cmake_rename_subdirectory(tests_cmake, old, new)
        _update_cmake_references(old, new, project_root, txn)

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
    tests_cmake = project_root / "tests" / "unit" / "CMakeLists.txt"
    new_tests_dir = project_root / "tests" / "unit" / dest
    dest_name = Path(dest).name

    # If dest basename differs from the original name, validate it as a safe library name
    if dest_name != name:
        validate_name(dest_name)

    has_tests = p.tests_dir.exists()

    if dry_run:
        print(f"[dry-run] move libs/{name} → libs/{dest}")
        if has_tests:
            print(f"[dry-run] move tests/unit/{name} → tests/unit/{dest}")
        return

    with Transaction(project_root) as txn:
        # ensure parent for new lib path
        if not new_dir.parent.exists():
            txn.safe_mkdir(new_dir.parent, parents=True, exist_ok=True)

        # move library directory
        txn.safe_rename(p.lib_dir, new_dir)

        # move tests dir if present
        if has_tests:
            if new_tests_dir.exists():
                raise FileExistsError(f"Destination tests directory '{new_tests_dir}' already exists")
            if not new_tests_dir.parent.exists():
                txn.safe_mkdir(new_tests_dir.parent, parents=True, exist_ok=True)
            txn.safe_rename(p.tests_dir, new_tests_dir)
            # update tests CMake registration
            _cmake_remove_subdirectory(tests_cmake, name)
            _cmake_add_subdirectory(tests_cmake, dest)

        # update libs CMake registration
        _cmake_remove_subdirectory(libs_cmake, name)
        _cmake_add_subdirectory(libs_cmake, dest)

        # If the final name changed (e.g. move to 'sub/newname'), update tokens and CMake references
        if dest_name != name:
            _replace_tokens_in_tree(new_dir, name, dest_name)
            if has_tests and new_tests_dir.exists():
                _replace_tokens_in_tree(new_tests_dir, name, dest_name)
            _update_cmake_references(name, dest_name, project_root, txn)

    print(f"✅ Moved: libs/{name} → libs/{dest}")
    if has_tests:
        print(f"✅ Moved tests: tests/unit/{name} → tests/unit/{dest}")
