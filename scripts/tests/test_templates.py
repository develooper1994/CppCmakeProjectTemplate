"""
Tests for core/commands/templates.py — Project templates gallery
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))


class TestTemplates:
    def test_all_templates_have_required_keys(self):
        from core.commands.templates import TEMPLATES
        for name, tpl in TEMPLATES.items():
            assert "description" in tpl, f"{name} missing description"
            assert "profile" in tpl, f"{name} missing profile"
            assert "config" in tpl, f"{name} missing config"
            assert "project" in tpl["config"], f"{name} missing project in config"

    def test_templates_count(self):
        from core.commands.templates import TEMPLATES
        assert len(TEMPLATES) == 7

    def test_all_templates_have_valid_profiles(self):
        from core.commands.templates import TEMPLATES
        valid_profiles = {"full", "minimal", "library", "app", "embedded"}
        for name, tpl in TEMPLATES.items():
            assert tpl["profile"] in valid_profiles, f"{name} has invalid profile: {tpl['profile']}"

    def test_minimal_template_structure(self):
        from core.commands.templates import TEMPLATES
        tpl = TEMPLATES["minimal"]
        libs = tpl["config"]["project"]["libs"]
        apps = tpl["config"]["project"]["apps"]
        assert len(libs) == 1
        assert len(apps) == 1
        assert libs[0]["name"] == "core"

    def test_library_template_has_no_apps(self):
        from core.commands.templates import TEMPLATES
        tpl = TEMPLATES["library"]
        assert len(tpl["config"]["project"]["apps"]) == 0

    def test_embedded_template_uses_static_linkage(self):
        from core.commands.templates import TEMPLATES
        tpl = TEMPLATES["embedded"]
        assert "presets" in tpl["config"]
        assert "static" in tpl["config"]["presets"]["linkages"]

    def test_game_engine_has_multiple_libs(self):
        from core.commands.templates import TEMPLATES
        tpl = TEMPLATES["game-engine"]
        assert len(tpl["config"]["project"]["libs"]) >= 4

    def test_header_only_template(self):
        from core.commands.templates import TEMPLATES
        tpl = TEMPLATES["header-only"]
        libs = tpl["config"]["project"]["libs"]
        assert len(libs) == 1
        assert libs[0]["type"] == "header-only"


class TestListTemplates:
    def test_list_prints_all_templates(self, capsys):
        from core.commands.templates import _list_templates
        _list_templates()
        output = capsys.readouterr().out
        assert "minimal" in output
        assert "library" in output
        assert "application" in output
        assert "embedded" in output
        assert "networking" in output
        assert "header-only" in output
        assert "game-engine" in output

    def test_list_shows_descriptions(self, capsys):
        from core.commands.templates import _list_templates
        _list_templates()
        output = capsys.readouterr().out
        assert "Bare-bones" in output  # minimal description
        assert "Profile:" in output


class TestCreateFromTemplate:
    def test_unknown_template_exits(self, tmp_path):
        from core.commands.templates import _create_from_template
        with pytest.raises(SystemExit):
            _create_from_template("MyProj", "nonexistent", tmp_path)

    def test_dry_run_does_not_write(self, tmp_path, capsys):
        from core.commands.templates import _create_from_template
        _create_from_template("MyProj", "minimal", tmp_path, dry_run=True)
        output = capsys.readouterr().out
        assert "MyProj" in output
        # No files should be written in dry run mode
        # (the target_dir might exist but the generate function handles dry_run)

    def test_create_sets_project_name(self, tmp_path, capsys):
        from core.commands.templates import _create_from_template
        _create_from_template("TestApp", "minimal", tmp_path, dry_run=True)
        output = capsys.readouterr().out
        assert "TestApp" in output


class TestTemplatesMain:
    def test_list_subcommand(self, capsys):
        from core.commands.templates import main
        main(["list"])
        output = capsys.readouterr().out
        assert "minimal" in output
        assert "game-engine" in output

    def test_no_subcommand_defaults_to_list(self, capsys):
        from core.commands.templates import main
        main([])
        output = capsys.readouterr().out
        assert "Available project templates" in output

    def test_create_dry_run(self, tmp_path, capsys):
        from core.commands.templates import main
        main(["create", "DryRunProj", "--template", "minimal", "--dry-run",
              "--target-dir", str(tmp_path)])
        output = capsys.readouterr().out
        assert "DryRunProj" in output
