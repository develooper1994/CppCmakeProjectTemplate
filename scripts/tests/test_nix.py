"""
Tests for core/commands/nix.py — Nix flake.nix generation
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))


@pytest.fixture
def nix_workspace(tmp_path, monkeypatch):
    """Minimal workspace for nix tests."""
    (tmp_path / "VERSION").write_text("2.0.0\n", encoding="utf-8")
    (tmp_path / "CMakeLists.txt").write_text(
        "project(NixTestProject VERSION 2.0.0 LANGUAGES CXX)\n",
        encoding="utf-8",
    )
    import core.commands.nix as nix_mod
    monkeypatch.setattr(nix_mod, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(nix_mod, "get_project_name", lambda: "NixTestProject")
    monkeypatch.setattr(nix_mod, "get_project_version", lambda: "2.0.0")
    return tmp_path


class TestGenerateFlakeNix:
    def test_contains_project_name(self):
        from core.commands.nix import _generate_flake_nix
        content = _generate_flake_nix("MyProject", "1.0.0")
        assert 'description = "MyProject' in content

    def test_contains_version(self):
        from core.commands.nix import _generate_flake_nix
        content = _generate_flake_nix("Proj", "3.5.0")
        assert 'version = "3.5.0"' in content

    def test_contains_cxx_standard(self):
        from core.commands.nix import _generate_flake_nix
        content = _generate_flake_nix("Proj", "1.0.0", cxx_std="20")
        assert "-DCMAKE_CXX_STANDARD=20" in content

    def test_default_cxx_standard_17(self):
        from core.commands.nix import _generate_flake_nix
        content = _generate_flake_nix("Proj", "1.0.0")
        assert "-DCMAKE_CXX_STANDARD=17" in content

    def test_has_devshell(self):
        from core.commands.nix import _generate_flake_nix
        content = _generate_flake_nix("Proj", "1.0.0")
        assert "devShells.default" in content
        assert "mkShell" in content

    def test_has_nixpkgs_input(self):
        from core.commands.nix import _generate_flake_nix
        content = _generate_flake_nix("Proj", "1.0.0")
        assert "nixpkgs.url" in content

    def test_has_packages_output(self):
        from core.commands.nix import _generate_flake_nix
        content = _generate_flake_nix("Proj", "1.0.0")
        assert "packages.default" in content
        assert "mkDerivation" in content


class TestNixMain:
    def test_dry_run_prints_content(self, nix_workspace, capsys):
        from core.commands.nix import main
        main(["generate", "--dry-run"])
        captured = capsys.readouterr()
        assert "NixTestProject" in captured.out
        assert "flake-utils" in captured.out
        # Should not write file
        assert not (nix_workspace / "flake.nix").exists()

    def test_generate_writes_flake(self, nix_workspace):
        from core.commands.nix import main
        main(["generate"])
        flake = nix_workspace / "flake.nix"
        assert flake.exists()
        content = flake.read_text(encoding="utf-8")
        assert "NixTestProject" in content

    def test_generate_creates_envrc(self, nix_workspace):
        from core.commands.nix import main
        main(["generate"])
        envrc = nix_workspace / ".envrc"
        assert envrc.exists()
        assert "use flake" in envrc.read_text(encoding="utf-8")

    def test_generate_does_not_overwrite_envrc(self, nix_workspace):
        envrc = nix_workspace / ".envrc"
        envrc.write_text("# custom direnv\n", encoding="utf-8")
        from core.commands.nix import main
        main(["generate"])
        assert envrc.read_text(encoding="utf-8") == "# custom direnv\n"

    def test_generate_custom_output(self, nix_workspace):
        out_dir = nix_workspace / "subdir"
        out_dir.mkdir()
        from core.commands.nix import main
        main(["generate", "--output", str(out_dir)])
        assert (out_dir / "flake.nix").exists()

    def test_no_subcommand_defaults_to_generate(self, nix_workspace):
        from core.commands.nix import main
        main([])
        assert (nix_workspace / "flake.nix").exists()
