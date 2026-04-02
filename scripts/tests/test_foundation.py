"""
Regression tests for Faz 0 (Foundation) changes.

Covers:
- cmake_parser.py: extract/set operations
- command_utils.py: wrap_command, add_common_args, apply_global_args
- jinja_helpers.py: JINJA_AVAILABLE flag
- Root-level scripts moved to new locations
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))


# ── cmake_parser tests ─────────────────────────────────────────────────────────

class TestCmakeParser:
    def test_extract_project_version(self, tmp_path: Path):
        from core.utils.cmake_parser import extract_project_version

        cm = tmp_path / "CMakeLists.txt"
        cm.write_text(
            'cmake_minimum_required(VERSION 3.22)\n'
            'project(MyProj VERSION 2.5.1 LANGUAGES CXX)\n',
            encoding="utf-8",
        )
        assert extract_project_version(cm) == "2.5.1"

    def test_extract_project_name(self, tmp_path: Path):
        from core.utils.cmake_parser import extract_project_name

        cm = tmp_path / "CMakeLists.txt"
        cm.write_text('project(FooBar VERSION 1.0.0 LANGUAGES CXX)\n', encoding="utf-8")
        assert extract_project_name(cm) == "FooBar"

    def test_extract_cmake_minimum_version(self, tmp_path: Path):
        from core.utils.cmake_parser import extract_cmake_minimum_version

        cm = tmp_path / "CMakeLists.txt"
        cm.write_text('cmake_minimum_required(VERSION 3.22)\nproject(X)\n', encoding="utf-8")
        assert extract_cmake_minimum_version(cm) == "3.22"

    def test_set_project_version(self, tmp_path: Path):
        from core.utils.cmake_parser import set_project_version, extract_project_version

        cm = tmp_path / "CMakeLists.txt"
        cm.write_text('project(X VERSION 1.0.0 LANGUAGES CXX)\n', encoding="utf-8")
        set_project_version(cm, "3.2.1")
        assert extract_project_version(cm) == "3.2.1"

    def test_add_subdirectory(self, tmp_path: Path):
        from core.utils.cmake_parser import add_subdirectory

        cm = tmp_path / "CMakeLists.txt"
        cm.write_text("# libs\n", encoding="utf-8")
        add_subdirectory(cm, "my_lib")
        content = cm.read_text(encoding="utf-8")
        assert "add_subdirectory(my_lib)" in content

    def test_remove_subdirectory(self, tmp_path: Path):
        from core.utils.cmake_parser import add_subdirectory, remove_subdirectory

        cm = tmp_path / "CMakeLists.txt"
        cm.write_text("add_subdirectory(foo)\nadd_subdirectory(bar)\n", encoding="utf-8")
        remove_subdirectory(cm, "foo")
        content = cm.read_text(encoding="utf-8")
        assert "foo" not in content
        assert "add_subdirectory(bar)" in content

    def test_rename_subdirectory(self, tmp_path: Path):
        from core.utils.cmake_parser import rename_subdirectory

        cm = tmp_path / "CMakeLists.txt"
        cm.write_text("add_subdirectory(old_lib)\n", encoding="utf-8")
        rename_subdirectory(cm, "old_lib", "new_lib")
        content = cm.read_text(encoding="utf-8")
        assert "old_lib" not in content
        assert "add_subdirectory(new_lib)" in content


# ── command_utils tests ────────────────────────────────────────────────────────

class TestCommandUtils:
    def test_wrap_command_success(self):
        from core.utils.command_utils import wrap_command
        from core.utils.common import CLIResult

        def ok_fn(args):
            pass

        result = wrap_command(ok_fn, None)
        assert result.success is True

    def test_wrap_command_system_exit_zero(self):
        from core.utils.command_utils import wrap_command

        def exit_zero(args):
            raise SystemExit(0)

        result = wrap_command(exit_zero, None)
        assert result.success is True

    def test_wrap_command_system_exit_nonzero(self):
        from core.utils.command_utils import wrap_command

        def exit_fail(args):
            raise SystemExit(2)

        result = wrap_command(exit_fail, None)
        assert result.success is False
        assert result.code == 2

    def test_add_common_args(self):
        from core.utils.command_utils import add_common_args

        parser = argparse.ArgumentParser()
        add_common_args(parser)
        args = parser.parse_args(["--dry-run", "--yes", "--json", "--verbose"])
        assert args.dry_run is True
        assert args.yes is True
        assert args.json is True
        assert args.verbose is True

    def test_apply_global_args(self):
        from core.utils.command_utils import apply_global_args
        from core.utils.common import GlobalConfig

        # Save and restore
        old = (GlobalConfig.DRY_RUN, GlobalConfig.YES, GlobalConfig.JSON, GlobalConfig.VERBOSE)
        try:
            ns = argparse.Namespace(dry_run=True, yes=True, json=False, verbose=False)
            apply_global_args(ns)
            assert GlobalConfig.DRY_RUN is True
            assert GlobalConfig.YES is True
        finally:
            GlobalConfig.DRY_RUN, GlobalConfig.YES, GlobalConfig.JSON, GlobalConfig.VERBOSE = old


# ── jinja_helpers tests ────────────────────────────────────────────────────────

class TestJinjaHelpers:
    def test_jinja_available_is_bool(self):
        from core.libpkg.jinja_helpers import JINJA_AVAILABLE
        assert isinstance(JINJA_AVAILABLE, bool)

    def test_render_template_file_works_when_jinja_available(self):
        pytest.importorskip("jinja2")
        from core.libpkg.jinja_helpers import render_template_file, JINJA_AVAILABLE
        assert JINJA_AVAILABLE is True
        out = render_template_file("readme.jinja2", name="testlib")
        assert "testlib" in out


# ── Module import smoke tests ─────────────────────────────────────────────────

class TestModuleImports:
    """Verify all refactored modules can be imported without error."""

    def test_import_cmake_parser(self):
        from core.utils.cmake_parser import extract_project_version
        assert callable(extract_project_version)

    def test_import_command_utils(self):
        from core.utils.command_utils import wrap_command
        assert callable(wrap_command)

    def test_import_sol_main(self):
        from core.commands.sol import main
        assert callable(main)

    def test_import_lib_main(self):
        from core.commands.lib import main
        assert callable(main)

    def test_import_session_cmds(self):
        from core.commands.session import cmd_save, cmd_load, cmd_set
        assert callable(cmd_save)

    def test_import_plugins_cmds(self):
        from core.commands.plugins import cmd_list
        assert callable(cmd_list)

    def test_import_release_impl(self):
        from core.release_impl import main
        assert callable(main)

    def test_import_init_impl(self):
        from core.init_impl import main
        assert callable(main)

    def test_import_verify_plugin(self):
        from plugins.verify import main
        assert callable(main)

    def test_import_publish_plugin(self):
        from plugins.publish import main
        assert callable(main)
