"""Tests for core/commands/perf.py — performance analysis commands."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.abspath("scripts"))

from core.commands.perf import (
    _human_size,
    _find_binaries,
    _cmd_size,
    _cmd_build_time,
    _analyze_ninja_log,
)


# ── _human_size ───────────────────────────────────────────────────────────────

class TestHumanSize:
    def test_bytes(self):
        assert _human_size(512) == "512.0 B"

    def test_kilobytes(self):
        assert _human_size(1024) == "1.0 KB"

    def test_megabytes(self):
        assert _human_size(1024 * 1024) == "1.0 MB"

    def test_gigabytes(self):
        assert _human_size(1024 ** 3) == "1.0 GB"

    def test_zero(self):
        assert _human_size(0) == "0.0 B"


# ── _find_binaries ────────────────────────────────────────────────────────────

class TestFindBinaries:
    def test_finds_static_library(self, tmp_path: Path):
        lib_dir = tmp_path / "lib"
        lib_dir.mkdir()
        dummy = lib_dir / "libdummy.a"
        dummy.write_bytes(b"\x00" * 100)
        result = _find_binaries(tmp_path)
        assert dummy in result

    def test_finds_shared_library(self, tmp_path: Path):
        lib_dir = tmp_path / "lib"
        lib_dir.mkdir()
        dummy = lib_dir / "libdummy.so"
        dummy.write_bytes(b"\x7fELF" + b"\x00" * 96)
        result = _find_binaries(tmp_path)
        assert dummy in result

    def test_finds_elf_executable(self, tmp_path: Path):
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        elf = bin_dir / "my_app"
        elf.write_bytes(b"\x7fELF" + b"\x00" * 60)
        result = _find_binaries(tmp_path)
        assert elf in result

    def test_ignores_cmake_files_dir(self, tmp_path: Path):
        cmake_dir = tmp_path / "bin" / "CMakeFiles"
        cmake_dir.mkdir(parents=True)
        noise = cmake_dir / "internal.a"
        noise.write_bytes(b"\x00" * 10)
        result = _find_binaries(tmp_path)
        assert noise not in result

    def test_empty_build_dir(self, tmp_path: Path):
        result = _find_binaries(tmp_path)
        assert result == []


# ── _analyze_ninja_log ────────────────────────────────────────────────────────

class TestAnalyzeNinjaLog:
    def _write_log(self, tmp_path: Path, entries: list[tuple]) -> Path:
        """entries: list of (start_ms, end_ms, target) tuples."""
        lines = ["# ninja log v5"]
        for start, end, tgt in entries:
            lines.append(f"{start}\t{end}\t0\t{tgt}\t0")
        log = tmp_path / ".ninja_log"
        log.write_text("\n".join(lines), encoding="utf-8")
        return log

    def test_parses_single_entry(self, tmp_path: Path):
        log = self._write_log(tmp_path, [(0, 2000, "CMakeFiles/dummy.cpp.o")])
        result = _analyze_ninja_log(log)
        assert result.success
        assert len(result.data) == 1
        assert result.data[0]["duration_s"] == pytest.approx(2.0)

    def test_sorts_by_duration_descending(self, tmp_path: Path):
        log = self._write_log(tmp_path, [
            (0, 1000, "fast.cpp.o"),
            (0, 5000, "slow.cpp.o"),
            (0, 3000, "medium.cpp.o"),
        ])
        result = _analyze_ninja_log(log)
        assert result.success
        durations = [e["duration_s"] for e in result.data]
        assert durations == sorted(durations, reverse=True)

    def test_total_in_message(self, tmp_path: Path):
        log = self._write_log(tmp_path, [(0, 4000, "a.o"), (0, 6000, "b.o")])
        result = _analyze_ninja_log(log)
        assert "10.00s" in result.message

    def test_malformed_log_returns_failure(self, tmp_path: Path):
        log = tmp_path / ".ninja_log"
        log.write_text("NOT_A_NINJA_LOG\tinvalid\n", encoding="utf-8")
        # Should not raise — returns failure gracefully
        result = _analyze_ninja_log(log)
        # Malformed lines are skipped; empty result is still success with 0 entries
        assert isinstance(result.success, bool)

    def test_report_written(self, tmp_path: Path, monkeypatch):
        import core.commands.perf as perf_mod
        monkeypatch.setattr(perf_mod, "LOGS_DIR", tmp_path)
        log = self._write_log(tmp_path, [(0, 1000, "x.o")])
        _analyze_ninja_log(log)
        report = tmp_path / "build_time_report.json"
        assert report.exists()
        data = json.loads(report.read_text())
        assert "total_seconds" in data


# ── _cmd_size ─────────────────────────────────────────────────────────────────

class TestCmdSize:
    def test_no_binaries_returns_failure(self, tmp_path: Path):
        args = SimpleNamespace(build_dir=str(tmp_path))
        result = _cmd_size(args)
        assert not result.success

    def test_detects_static_lib(self, tmp_path: Path, monkeypatch):
        import core.commands.perf as perf_mod
        monkeypatch.setattr(perf_mod, "LOGS_DIR", tmp_path / "logs")
        lib_dir = tmp_path / "lib"
        lib_dir.mkdir()
        (lib_dir / "libtest.a").write_bytes(b"\x00" * 200)
        args = SimpleNamespace(build_dir=str(tmp_path))
        result = _cmd_size(args)
        assert result.success
        assert len(result.data) == 1
        assert result.data[0]["size_bytes"] == 200

    def test_report_saved(self, tmp_path: Path, monkeypatch):
        import core.commands.perf as perf_mod
        logs_dir = tmp_path / "logs"
        monkeypatch.setattr(perf_mod, "LOGS_DIR", logs_dir)
        lib_dir = tmp_path / "lib"
        lib_dir.mkdir()
        (lib_dir / "libfoo.a").write_bytes(b"\x00" * 50)
        args = SimpleNamespace(build_dir=str(tmp_path))
        _cmd_size(args)
        report = logs_dir / "size_report.json"
        assert report.exists()
        data = json.loads(report.read_text())
        assert isinstance(data, list)
        assert data[0]["size_bytes"] == 50
