"""
Tests for core/commands/deps.py — Dependency management.
"""
from __future__ import annotations

import sys
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_SCRIPTS = Path(__file__).resolve().parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))


@pytest.fixture
def deps_mod(tmp_path, monkeypatch):
    import core.commands.deps as deps
    monkeypatch.setattr(deps, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(deps, "VCPKG_JSON", tmp_path / "vcpkg.json")
    monkeypatch.setattr(deps, "VCPKG_LOCK", tmp_path / "vcpkg.lock.json")
    monkeypatch.setattr(deps, "CONAN_FILE", tmp_path / "conanfile.py")
    monkeypatch.setattr(deps, "CONAN_LOCK", tmp_path / "conan.lock")
    monkeypatch.setattr(deps, "REQ_FILE", tmp_path / "requirements-dev.txt")
    monkeypatch.setattr(deps, "PIP_LOCK", tmp_path / "requirements-dev.lock.txt")
    return deps


class TestDepsList:
    def test_list_all_managers(self, deps_mod, capsys):
        # Create manifests
        deps_mod.VCPKG_JSON.write_text(json.dumps({"dependencies": ["zlib"]}))
        deps_mod.CONAN_FILE.write_text("self.requires('fmt/10.2.1')")
        deps_mod.REQ_FILE.write_text("pytest>=7.0")

        from core.commands.deps import main
        with pytest.raises(SystemExit):
            main(["list"])
        captured = capsys.readouterr()
        assert "[vcpkg]" in captured.out
        assert "zlib" in captured.out
        assert "[conan]" in captured.out
        assert "fmt/10.2.1" in captured.out
        assert "[pip]" in captured.out
        assert "pytest>=7.0" in captured.out

    def test_list_empty(self, deps_mod):
        from core.commands.deps import main
        with pytest.raises(SystemExit) as exc:
            main(["list"])
        assert exc.value.code == 1


class TestDepsVerify:
    def test_verify_up_to_date(self, deps_mod, capsys):
        v_json = deps_mod.VCPKG_JSON
        v_json.write_text(json.dumps({"dependencies": ["zlib"]}))
        
        from core.commands.deps import _sha256_file
        v_lock = deps_mod.VCPKG_LOCK
        v_lock.write_text(json.dumps({"manifest-hash": _sha256_file(v_json)}))

        from core.commands.deps import main
        with pytest.raises(SystemExit):
            main(["verify"])
        captured = capsys.readouterr()
        assert "✓ vcpkg.lock.json up-to-date" in captured.out

    def test_verify_stale(self, deps_mod, capsys):
        v_json = deps_mod.VCPKG_JSON
        v_json.write_text(json.dumps({"dependencies": ["zlib"]}))
        v_lock = deps_mod.VCPKG_LOCK
        v_lock.write_text(json.dumps({"manifest-hash": "wrong-hash"}))

        from core.commands.deps import main
        with pytest.raises(SystemExit) as exc:
            main(["verify"])
        captured = capsys.readouterr()
        # Logger.error can write to out or err depending on config.
        # But we saw it in captured.out in the previous run.
        all_output = captured.out + captured.err
        assert "stale" in all_output
        assert exc.value.code == 1


class TestDepsUpdate:
    @patch("core.commands.deps._pip_outdated")
    def test_update_pip(self, mock_pip, deps_mod, capsys):
        mock_pip.return_value = [{"name": "pytest", "version": "7.0", "latest_version": "8.0"}]
        deps_mod.REQ_FILE.write_text("pytest>=7.0")
        
        from core.commands.deps import main
        with pytest.raises(SystemExit):
            main(["update", "--managers", "pip"])
        captured = capsys.readouterr()
        assert "pytest: 7.0 → 8.0" in captured.out

    def test_update_vcpkg_tips(self, deps_mod, capsys):
        deps_mod.VCPKG_JSON.write_text(json.dumps({"dependencies": ["zlib"]}))
        from core.commands.deps import main
        with pytest.raises(SystemExit):
            main(["update", "--managers", "vcpkg"])
        captured = capsys.readouterr()
        assert "zlib (pinned: *)" in captured.out
        assert "Tip: run 'vcpkg upgrade'" in captured.out


class TestDepsLock:
    def test_lock_vcpkg_dry_run(self, deps_mod, capsys):
        deps_mod.VCPKG_JSON.write_text(json.dumps({"dependencies": ["zlib"]}))
        from core.commands.deps import main
        with pytest.raises(SystemExit):
            main(["lock", "--dry-run", "--managers", "vcpkg"])
        captured = capsys.readouterr()
        assert "[dry-run] Would write" in captured.out
        assert not deps_mod.VCPKG_LOCK.exists()
