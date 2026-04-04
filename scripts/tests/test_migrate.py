"""
Tests for core/commands/migrate.py — Migration wizard
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))


@pytest.fixture
def migrate_workspace(tmp_path, monkeypatch):
    """Workspace with a generation manifest."""
    from core.utils.common import GlobalConfig
    monkeypatch.setattr(GlobalConfig, "JSON", False)
    (tmp_path / "VERSION").write_text("1.0.0\n", encoding="utf-8")
    (tmp_path / "CMakeLists.txt").write_text(
        "project(MigrateProject VERSION 1.0.0 LANGUAGES CXX)\n",
        encoding="utf-8",
    )
    import core.commands.migrate as migrate_mod
    monkeypatch.setattr(migrate_mod, "PROJECT_ROOT", tmp_path)
    return tmp_path


def _write_manifest(root: Path, files: dict[str, str] | None = None):
    """Create a .tool/generation_manifest.json with file hashes."""
    tool_dir = root / ".tool"
    tool_dir.mkdir(exist_ok=True)
    manifest_files = {}
    if files:
        for rel_path, content in files.items():
            full = root / rel_path
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(content, encoding="utf-8")
            h = hashlib.sha256(full.read_bytes()).hexdigest()
            manifest_files[rel_path] = {"hash": h}
    manifest = {"files": manifest_files}
    (tool_dir / "generation_manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    return manifest


class TestReadManifest:
    def test_returns_none_without_manifest(self, migrate_workspace):
        from core.commands.migrate import _read_manifest
        assert _read_manifest() is None

    def test_reads_valid_manifest(self, migrate_workspace):
        _write_manifest(migrate_workspace, {"foo.txt": "hello"})
        from core.commands.migrate import _read_manifest
        manifest = _read_manifest()
        assert manifest is not None
        assert "foo.txt" in manifest["files"]

    def test_returns_none_on_corrupt_json(self, migrate_workspace):
        tool_dir = migrate_workspace / ".tool"
        tool_dir.mkdir()
        (tool_dir / "generation_manifest.json").write_text("not json!", encoding="utf-8")
        from core.commands.migrate import _read_manifest
        assert _read_manifest() is None


class TestReadVersion:
    def test_reads_version_file(self, migrate_workspace):
        from core.commands.migrate import _read_version
        assert _read_version() == "1.0.0"

    def test_unknown_without_version_file(self, tmp_path, monkeypatch):
        import core.commands.migrate as migrate_mod
        monkeypatch.setattr(migrate_mod, "PROJECT_ROOT", tmp_path)
        from core.commands.migrate import _read_version
        assert _read_version() == "unknown"


class TestDetectDrift:
    def test_no_drift_when_unchanged(self, migrate_workspace):
        manifest = _write_manifest(migrate_workspace, {"a.txt": "content"})
        from core.commands.migrate import _detect_drift
        drifted = _detect_drift(manifest)
        assert drifted == []

    def test_detects_modified_file(self, migrate_workspace):
        manifest = _write_manifest(migrate_workspace, {"a.txt": "original"})
        # Modify the file after manifest was created
        (migrate_workspace / "a.txt").write_text("changed", encoding="utf-8")
        from core.commands.migrate import _detect_drift
        drifted = _detect_drift(manifest)
        assert len(drifted) == 1
        assert drifted[0]["status"] == "modified"
        assert drifted[0]["file"] == "a.txt"

    def test_detects_deleted_file(self, migrate_workspace):
        manifest = _write_manifest(migrate_workspace, {"b.txt": "content"})
        (migrate_workspace / "b.txt").unlink()
        from core.commands.migrate import _detect_drift
        drifted = _detect_drift(manifest)
        assert len(drifted) == 1
        assert drifted[0]["status"] == "deleted"

    def test_no_drift_empty_manifest(self, migrate_workspace):
        manifest = {"files": {}}
        from core.commands.migrate import _detect_drift
        drifted = _detect_drift(manifest)
        assert drifted == []

    def test_skip_files_without_hash(self, migrate_workspace):
        (migrate_workspace / "c.txt").write_text("data", encoding="utf-8")
        manifest = {"files": {"c.txt": {}}}  # no hash key
        from core.commands.migrate import _detect_drift
        drifted = _detect_drift(manifest)
        assert drifted == []


class TestCheckUpgradeable:
    def test_no_manifest_recommends_generate(self, migrate_workspace):
        from core.commands.migrate import _check_upgradeable
        result = _check_upgradeable()
        assert result["has_manifest"] is False
        assert any("generate" in r.lower() for r in result["recommendations"])

    def test_with_clean_manifest(self, migrate_workspace):
        _write_manifest(migrate_workspace, {"x.txt": "data"})
        from core.commands.migrate import _check_upgradeable
        result = _check_upgradeable()
        assert result["has_manifest"] is True
        assert result["drift"] == []
        assert any("no drift" in r.lower() for r in result["recommendations"])

    def test_with_drifted_manifest(self, migrate_workspace):
        _write_manifest(migrate_workspace, {"y.txt": "original"})
        (migrate_workspace / "y.txt").write_text("modified", encoding="utf-8")
        from core.commands.migrate import _check_upgradeable
        result = _check_upgradeable()
        assert len(result["drift"]) == 1
        assert any("modified" in r.lower() for r in result["recommendations"])


class TestMigrateMain:
    def test_check_mode_no_manifest(self, migrate_workspace, capsys):
        from core.commands.migrate import main
        main(["--check"])
        output = capsys.readouterr().out
        assert "not found" in output.lower()

    def test_check_mode_with_manifest(self, migrate_workspace, capsys):
        _write_manifest(migrate_workspace, {"z.txt": "data"})
        from core.commands.migrate import main
        main(["--check"])
        output = capsys.readouterr().out
        assert "no drift" in output.lower()

    def test_check_mode_with_drift(self, migrate_workspace, capsys):
        _write_manifest(migrate_workspace, {"d.txt": "orig"})
        (migrate_workspace / "d.txt").write_text("changed", encoding="utf-8")
        from core.commands.migrate import main
        main(["--check"])
        output = capsys.readouterr().out
        assert "drift" in output.lower()

    def test_no_manifest_exits(self, migrate_workspace):
        from core.commands.migrate import main
        with pytest.raises(SystemExit):
            main([])
