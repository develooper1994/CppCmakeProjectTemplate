import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

# Ensure the `scripts` package is importable when running pytest from the repository root
sys.path.insert(0, os.path.abspath("scripts"))

from core.libpkg import create as create_mod


def setup_minimal_project(root: Path):
    (root / "libs").mkdir()
    (root / "libs" / "CMakeLists.txt").write_text("# libs root\n", encoding="utf-8")
    (root / "tests").mkdir()
    (root / "tests" / "unit").mkdir(parents=True)
    (root / "tests" / "unit" / "CMakeLists.txt").write_text("# tests root\n", encoding="utf-8")


def test_remove_detach_and_delete(tmp_path: Path):
    root = tmp_path
    setup_minimal_project(root)

    # create a library
    create_mod.create_library("toy", dry_run=False, root=root)

    import core.commands.lib as lib_cmd

    # Point CLI module to our tmp project root
    lib_cmd.PROJECT_ROOT = root

    # Detach (remove CMake registration, keep files)
    args = SimpleNamespace(name="toy", delete=False, dry_run=False)
    lib_cmd._impl_cmd_remove(args)

    # Library folder should still exist
    assert (root / "libs" / "toy").exists()

    # CMake registration should be removed
    libs_cmake = (root / "libs" / "CMakeLists.txt").read_text(encoding="utf-8")
    assert "add_subdirectory(toy)" not in libs_cmake

    # Now delete
    args = SimpleNamespace(name="toy", delete=True, dry_run=False)
    lib_cmd._impl_cmd_remove(args)
    assert not (root / "libs" / "toy").exists()


def test_rename_library_updates_files_and_cmake(tmp_path: Path):
    root = tmp_path
    setup_minimal_project(root)
    create_mod.create_library("oldlib", dry_run=False, root=root)

    import core.commands.lib as lib_cmd
    lib_cmd.PROJECT_ROOT = root

    args = SimpleNamespace(old="oldlib", new="newlib", dry_run=False)
    lib_cmd._impl_cmd_rename(args)

    assert not (root / "libs" / "oldlib").exists()
    assert (root / "libs" / "newlib").exists()
    libs_cmake = (root / "libs" / "CMakeLists.txt").read_text(encoding="utf-8")
    assert "add_subdirectory(newlib)" in libs_cmake


def test_move_library_updates_cmake_and_path(tmp_path: Path):
    root = tmp_path
    setup_minimal_project(root)
    create_mod.create_library("movelib", dry_run=False, root=root)

    import core.commands.lib as lib_cmd
    lib_cmd.PROJECT_ROOT = root

    args = SimpleNamespace(name="movelib", dest="subdir/movelib", dry_run=False)
    lib_cmd._impl_cmd_move(args)

    assert not (root / "libs" / "movelib").exists()
    assert (root / "libs" / "subdir" / "movelib").exists()
    libs_cmake = (root / "libs" / "CMakeLists.txt").read_text(encoding="utf-8")
    assert "add_subdirectory(subdir/movelib)" in libs_cmake
