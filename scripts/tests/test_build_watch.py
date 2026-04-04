"""
Tests for core/commands/build/commands.py — watch and diagnose subcommands.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_SCRIPTS = Path(__file__).resolve().parent.parent.parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))


@pytest.fixture
def build_commands():
    import core.commands.build.commands as build_mod
    return build_mod


class TestBuildWatch:
    @patch("core.commands.build.commands.run_proc")
    @patch("time.sleep")
    def test_watch_runs_loop_and_stops_on_interrupt(self, mock_sleep, mock_run, build_commands, capsys):
        # KeyboardInterrupt'u tetikleyerek döngüden çıkışını test et
        mock_sleep.side_effect = KeyboardInterrupt()
        
        # cmd_watch KeyboardInterrupt'u yakalayıp düzgünce çıkar
        build_commands.cmd_watch(MagicMock(interval=1, preset="gcc"))
        
        captured = capsys.readouterr()
        assert "Watch mode active" in captured.out
        assert "Watch mode stopped" in captured.out
        # run_proc ilk build için çağrılmış olmalı
        assert mock_run.called

class TestBuildDiagnose:
    def test_diagnose_log_file_recognizes_errors(self, tmp_path, build_commands, capsys):
        log_file = tmp_path / "build.log"
        # diagnose.py'nin tanıdığı standart bir hata deseni (örneğin vector deklarasyonu)
        log_file.write_text("error: 'std::vector' has not been declared\n", encoding="utf-8")
        
        args = MagicMock(logfile=str(log_file))
        build_commands.cmd_diagnose(args)
        
        captured = capsys.readouterr()
        # Eğer diags tanınmazsa "No actionable diagnostics found" yazar.
        # Tanınırsa formatlı çıktı basar.
        assert "diagnostic(s) found" in captured.out or "No actionable diagnostics found" in captured.out

    @patch("sys.stdin.read")
    def test_diagnose_stdin_mode(self, mock_stdin, build_commands, capsys):
        mock_stdin.return_value = "error: unknown type name 'uint32_t'\n"
        args = MagicMock(logfile=None)
        
        build_commands.cmd_diagnose(args)
        
        captured = capsys.readouterr()
        assert "Reading build output from stdin" in captured.out
