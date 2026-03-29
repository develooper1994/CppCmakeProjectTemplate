import os
import sys
from pathlib import Path

import pytest

# Ensure the `scripts` package is importable when running pytest from the repository root
sys.path.insert(0, os.path.abspath("scripts"))

from core.libpkg import templates
from core.libpkg import create as create_mod


def test_lib_header_contains_guard_and_namespace():
    out = templates.lib_header("mylib", "myns")
    assert "#pragma once" in out
    assert "namespace myns" in out


def test_lib_cmakelists_has_add_library_and_includes():
    out = templates.lib_cmakelists("mylib", "1.0.0", "myns", [], "17")
    assert "add_library(" in out
    assert "target_include_directories(" in out


def test_render_readme_jinja_if_available():
    # Only run this test when jinja2 is installed
    pytest.importorskip("jinja2")
    from core.libpkg.jinja_helpers import render_template_file

    out = render_template_file("readme.jinja2", name="coollib")
    assert "# coollib" in out
    assert "Generated library: coollib" in out


def test_create_library_writes_files_and_registers(tmp_path: Path):
    root = tmp_path
    # Create minimal CMakeLists targets required by create_library
    (root / "libs").mkdir()
    (root / "libs" / "CMakeLists.txt").write_text("# libs root\n", encoding="utf-8")
    (root / "tests").mkdir()
    (root / "tests" / "unit").mkdir(parents=True)
    (root / "tests" / "unit" / "CMakeLists.txt").write_text("# tests root\n", encoding="utf-8")

    # call create_library
    create_mod.create_library("toy", dry_run=False, root=root)

    lib_dir = root / "libs" / "toy"
    assert lib_dir.exists()
    assert (lib_dir / "include" / "toy" / "toy.h").exists()
    assert (lib_dir / "src" / "toy.cpp").exists()
    # CMake registration
    libs_cmake = (root / "libs" / "CMakeLists.txt").read_text(encoding="utf-8")
    assert "add_subdirectory(toy)" in libs_cmake or "add_subdirectory( toy )" in libs_cmake


def test_create_library_duplicate_raises(tmp_path: Path):
    root = tmp_path
    (root / "libs").mkdir()
    (root / "libs" / "CMakeLists.txt").write_text("", encoding="utf-8")
    (root / "tests").mkdir()
    (root / "tests" / "unit").mkdir(parents=True)
    (root / "tests" / "unit" / "CMakeLists.txt").write_text("", encoding="utf-8")

    create_mod.create_library("dup", dry_run=False, root=root)
    with pytest.raises(FileExistsError):
        create_mod.create_library("dup", dry_run=False, root=root)
