"""
Tests for core/commands/diagnostics.py — Build error diagnostics
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))


class TestDiagnoseOutput:
    """Test the diagnose_output() function against known patterns."""

    def test_unknown_cmake_command(self):
        from core.commands.diagnostics import diagnose_output
        text = 'CMake Error: Unknown CMake command "target_foobar".'
        results = diagnose_output(text)
        assert len(results) == 1
        assert "target_foobar" in results[0]["explanation"]
        assert "include()" in results[0]["suggestion"]

    def test_package_not_found(self):
        from core.commands.diagnostics import diagnose_output
        text = "CMake Error: Could not find package 'Boost'"
        results = diagnose_output(text)
        assert len(results) == 1
        assert "Boost" in results[0]["explanation"]

    def test_cmake_version_too_low(self):
        from core.commands.diagnostics import diagnose_output
        text = "CMake 3.25 or higher is required. You are running version 3.16."
        results = diagnose_output(text)
        assert len(results) == 1
        assert "3.25" in results[0]["explanation"]
        assert "Upgrade" in results[0]["suggestion"]

    def test_undefined_reference(self):
        from core.commands.diagnostics import diagnose_output
        text = "error: undefined reference to `MyClass::doStuff()'"
        results = diagnose_output(text)
        assert len(results) == 1
        assert "MyClass" in results[0]["explanation"]
        assert "target_link_libraries" in results[0]["suggestion"]

    def test_missing_header(self):
        from core.commands.diagnostics import diagnose_output
        text = "fatal error: boost/asio.hpp: No such file or directory"
        results = diagnose_output(text)
        assert len(results) == 1
        assert "boost/asio.hpp" in results[0]["explanation"]

    def test_no_member_named(self):
        from core.commands.diagnostics import diagnose_output
        text = "error: no member named 'frobnicate' in 'std::vector'"
        results = diagnose_output(text)
        assert len(results) == 1
        assert "frobnicate" in results[0]["explanation"]

    def test_no_rule_to_make_target(self):
        from core.commands.diagnostics import diagnose_output
        text = "No rule to make target 'src/missing.cpp'"
        results = diagnose_output(text)
        assert len(results) == 1
        assert "src/missing.cpp" in results[0]["explanation"]

    def test_permission_denied(self):
        from core.commands.diagnostics import diagnose_output
        text = "error: Permission denied while writing to /usr/local/lib"
        results = diagnose_output(text)
        assert len(results) == 1
        assert "Permission denied" in results[0]["explanation"]

    def test_out_of_memory(self):
        from core.commands.diagnostics import diagnose_output
        text = "c++: fatal error: out of memory allocating 1234 bytes"
        results = diagnose_output(text)
        assert len(results) == 1
        assert "memory" in results[0]["explanation"].lower()

    def test_preset_not_found(self):
        from core.commands.diagnostics import diagnose_output
        text = 'Could not find a preset named "gcc-super-preset"'
        results = diagnose_output(text)
        assert len(results) == 1
        assert "gcc-super-preset" in results[0]["explanation"]

    def test_clean_output_no_matches(self):
        from core.commands.diagnostics import diagnose_output
        text = "[100%] Built target main_app\nBuild complete."
        results = diagnose_output(text)
        assert results == []

    def test_multiple_errors(self):
        from core.commands.diagnostics import diagnose_output
        text = (
            "fatal error: foo.h: No such file or directory\n"
            "error: undefined reference to `bar()'\n"
            "Build ran out of memory.\n"
        )
        results = diagnose_output(text)
        assert len(results) == 3

    def test_deduplicates_same_pattern(self):
        from core.commands.diagnostics import diagnose_output
        text = (
            "error: undefined reference to `foo()'\n"
            "error: undefined reference to `foo()'\n"
        )
        results = diagnose_output(text)
        assert len(results) == 1


class TestFormatDiagnostic:
    def test_format_contains_error_code(self):
        from core.commands.diagnostics import _format_diagnostic
        diag = {
            "error": "some error",
            "explanation": "Something went wrong",
            "suggestion": "Fix it",
        }
        formatted = _format_diagnostic(diag, 1)
        assert "E0001" in formatted
        assert "Something went wrong" in formatted
        assert "Fix it" in formatted


class TestDiagnosticsMain:
    @pytest.fixture(autouse=True)
    def _reset_globals(self, monkeypatch):
        from core.utils.common import GlobalConfig
        monkeypatch.setattr(GlobalConfig, "JSON", False)

    def test_log_file_analysis(self, tmp_path, monkeypatch):
        import core.commands.diagnostics as diag_mod
        monkeypatch.setattr(diag_mod, "PROJECT_ROOT", tmp_path)

        log = tmp_path / "build.log"
        log.write_text(
            'CMake Error: Unknown CMake command "my_func".\n',
            encoding="utf-8",
        )
        from core.commands.diagnostics import main
        main(["--log", str(log)])
        # Should not raise — just prints diagnostics

    def test_no_log_graceful(self, tmp_path, monkeypatch, capsys):
        import core.commands.diagnostics as diag_mod
        monkeypatch.setattr(diag_mod, "PROJECT_ROOT", tmp_path)

        from core.commands.diagnostics import main
        main([])
        output = capsys.readouterr().out
        assert "No build log found" in output

    def test_clean_log(self, tmp_path, monkeypatch, capsys):
        import core.commands.diagnostics as diag_mod
        monkeypatch.setattr(diag_mod, "PROJECT_ROOT", tmp_path)

        (tmp_path / "build_logs").mkdir()
        log = tmp_path / "build_logs" / "tool.log"
        log.write_text("Build succeeded.\n", encoding="utf-8")

        from core.commands.diagnostics import main
        main([])
        output = capsys.readouterr().out
        assert "No known error patterns" in output
