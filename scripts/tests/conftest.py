"""
Shared pytest fixtures for the CppCmakeProjectTemplate tooling test suite.

Provides WorkspaceFixture — a minimal project skeleton in tmp_path that
allows testing library CRUD, CMake parsing, and command dispatch without
touching the real repository.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Ensure scripts/ is on sys.path for all test modules
_SCRIPTS = Path(__file__).resolve().parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))


class WorkspaceFixture:
    """A minimal project workspace for integration tests.

    Provides:
    - root/CMakeLists.txt  (with project() declaration)
    - root/libs/CMakeLists.txt
    - root/tests/unit/CMakeLists.txt
    - root/apps/CMakeLists.txt
    - root/VERSION
    """

    def __init__(self, root: Path) -> None:
        self.root = root
        self._setup()

    def _setup(self) -> None:
        r = self.root

        # Top-level CMakeLists.txt
        (r / "CMakeLists.txt").write_text(
            'cmake_minimum_required(VERSION 3.22)\n'
            'project(TestProject VERSION 1.0.0 LANGUAGES CXX)\n'
            'set(CMAKE_CXX_STANDARD 17)\n'
            'add_subdirectory(libs)\n'
            'add_subdirectory(apps)\n',
            encoding="utf-8",
        )

        # VERSION file
        (r / "VERSION").write_text("1.0.0\n", encoding="utf-8")

        # libs/
        (r / "libs").mkdir()
        (r / "libs" / "CMakeLists.txt").write_text("# libs root\n", encoding="utf-8")

        # tests/unit/
        (r / "tests" / "unit").mkdir(parents=True)
        (r / "tests" / "unit" / "CMakeLists.txt").write_text("# tests root\n", encoding="utf-8")

        # apps/
        (r / "apps").mkdir()
        (r / "apps" / "CMakeLists.txt").write_text("# apps root\n", encoding="utf-8")


@pytest.fixture
def workspace(tmp_path: Path) -> WorkspaceFixture:
    """Create a minimal project workspace for testing."""
    return WorkspaceFixture(tmp_path)
