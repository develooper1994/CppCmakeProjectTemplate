"""
Tests for plugins/setup.py — Dependency checker/installer plugin.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_SCRIPTS = Path(__file__).resolve().parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))


@pytest.fixture
def setup_plugin():
    import plugins.setup as setup_mod
    return setup_mod


class TestSetupCheck:
    def test_check_all_dependencies_returns_list(self, setup_plugin):
        results = setup_plugin.check_all_dependencies()
        assert isinstance(results, list)
        assert len(results) > 0
        assert any(r["name"] == "critical_build" for r in results)

    def test_check_specific_category(self, setup_plugin):
        results = setup_plugin.check_all_dependencies(categories=["compiler"])
        assert len(results) == 1
        assert results[0]["name"] == "compiler"

    def test_print_dependency_report_no_errors(self, setup_plugin, capsys):
        # Mock results where everything is OK
        results = [{
            "name": "test_cat",
            "description": "test desc",
            "required": True,
            "status": "ok",
            "found": {"tool": {"version": "1.0", "type": "binary"}},
            "missing": {}
        }]
        errors = setup_plugin.print_dependency_report(results)
        captured = capsys.readouterr()
        assert errors == 0
        assert "✅ test_cat" in captured.out
        assert "✅ tool" in captured.out

    def test_print_dependency_report_with_errors(self, setup_plugin, capsys):
        results = [{
            "name": "critical",
            "description": "desc",
            "required": True,
            "status": "error",
            "found": {},
            "missing": {"gcc": "build-essential"}
        }]
        errors = setup_plugin.print_dependency_report(results)
        captured = capsys.readouterr()
        assert errors == 1
        assert "❌ critical" in captured.out
        assert "❌ gcc" in captured.out


class TestSetupDetect:
    def test_detect_environment_returns_dict(self, setup_plugin):
        info = setup_plugin.detect_environment()
        assert isinstance(info, dict)
        assert "os" in info
        assert "arch" in info
        assert "compilers" in info
        assert "features" in info

    def test_print_environment_report(self, setup_plugin, capsys):
        info = {
            "os": "Linux",
            "os_release": "5.15",
            "arch": "x86_64",
            "python_version": "3.12.0",
            "package_manager": "apt",
            "compilers": {"gcc": "11.4.0"},
            "features": {"ccache": True, "ninja": False}
        }
        setup_plugin.print_environment_report(info)
        captured = capsys.readouterr()
        assert "OS:              Linux" in captured.out
        assert "gcc            11.4.0" in captured.out
        assert "✅ ccache" in captured.out
        assert "⬚  ninja" in captured.out


class TestSetupMain:
    @patch("plugins.setup.check_all_dependencies")
    @patch("plugins.setup.print_dependency_report")
    def test_main_check_mode(self, mock_report, mock_check, setup_plugin):
        mock_check.return_value = []
        mock_report.return_value = 0
        setup_plugin.main(["--check"])
        mock_check.assert_called_once()
        mock_report.assert_called_once()

    @patch("plugins.setup.detect_environment")
    @patch("plugins.setup.print_environment_report")
    def test_main_detect_mode(self, mock_report, mock_detect, setup_plugin):
        mock_detect.return_value = {}
        setup_plugin.main(["--detect"])
        mock_detect.assert_called_once()
        mock_report.assert_called_once()

    @patch("plugins.setup.find_missing_binaries")
    def test_main_install_mode_dry_run(self, mock_find, setup_plugin, capsys):
        mock_find.return_value = {"cmake": "cmake"}
        # Should print missing and offer --install
        setup_plugin.main([])
        captured = capsys.readouterr()
        assert "Missing system dependencies" in captured.out
        assert "cmake" in captured.out
        assert "Re-run with --install" in captured.out
