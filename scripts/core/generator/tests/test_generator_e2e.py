"""
E2E tests for the generator engine.

Validates:
  - All components generate files without errors
  - Fresh-directory generation produces expected file count
  - Idempotent regeneration skips all files
  - Conflict detection with --force overwrites modified files
  - Per-component generation works (--component)
  - Manifest tracks all generated files
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

# Ensure scripts/ is on sys.path
_scripts_dir = Path(__file__).resolve().parents[3]
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

from core.commands import generate as generate_cmd
from core.generator.engine import generate, build_context, COMPONENT_REGISTRY, GenerateResult
from core.generator.merge import ConflictPolicy
from core.generator.wizard import Wizard, WizardAnswers


@pytest.fixture
def target_dir(tmp_path):
    """Create a clean temporary directory for generation."""
    return tmp_path / "project"


@pytest.fixture
def ctx():
    return build_context()


class TestGeneratorE2E:
    """End-to-end tests for the full generation pipeline."""

    def test_fresh_generation(self, target_dir):
        """Generating into an empty directory should create all files."""
        result = generate(target_dir, policy=ConflictPolicy.OVERWRITE)
        assert result.total > 0
        assert len(result.errors) == 0
        assert len(result.created) == result.total
        assert len(result.skipped) == 0

    def test_idempotent_regeneration(self, target_dir):
        """Second run should skip all files (content unchanged)."""
        generate(target_dir, policy=ConflictPolicy.OVERWRITE)
        result2 = generate(target_dir, policy=ConflictPolicy.OVERWRITE)
        assert len(result2.errors) == 0
        assert len(result2.skipped) == result2.total
        assert len(result2.created) == 0
        assert len(result2.written) == 0

    def test_conflict_detection_force(self, target_dir):
        """Modified file should be overwritten with --force."""
        generate(target_dir, policy=ConflictPolicy.OVERWRITE)

        # Modify a generated file
        cmake_path = target_dir / "CMakeLists.txt"
        assert cmake_path.exists()
        cmake_path.write_text(cmake_path.read_text() + "\n# user edit\n")

        # Regenerate with force
        result = generate(target_dir, policy=ConflictPolicy.OVERWRITE)
        assert "CMakeLists.txt" in result.written

    def test_conflict_detection_skip(self, target_dir):
        """Modified file should be skipped with SKIP policy."""
        generate(target_dir, policy=ConflictPolicy.OVERWRITE)

        cmake_path = target_dir / "CMakeLists.txt"
        cmake_path.write_text(cmake_path.read_text() + "\n# user edit\n")

        result = generate(target_dir, policy=ConflictPolicy.SKIP)
        assert "CMakeLists.txt" in result.skipped

    def test_per_component_generation(self, target_dir):
        """Single component generation should only produce that component's files."""
        result = generate(
            target_dir,
            components=["cmake-root"],
            policy=ConflictPolicy.OVERWRITE,
        )
        assert len(result.errors) == 0
        assert result.total > 0
        # cmake-root generates: CMakeLists.txt, libs/, apps/, tests/ aggregators
        assert any("CMakeLists.txt" in f for f in result.created)

    def test_manifest_integrity(self, target_dir):
        """Manifest should track all generated files with valid hashes."""
        result = generate(target_dir, policy=ConflictPolicy.OVERWRITE)
        manifest_path = target_dir / ".tool" / "generation_manifest.json"
        assert manifest_path.exists()

        with open(manifest_path) as f:
            manifest = json.load(f)

        assert manifest["version"] == 1
        assert len(manifest["files"]) == result.total

        # Every file should have a hash and component
        for rel_path, info in manifest["files"].items():
            assert "hash" in info
            assert "component" in info
            assert "generated_at" in info
            assert len(info["hash"]) == 64  # SHA256

    def test_all_components_registered(self):
        """All expected components should be in the registry."""
        expected = {
            "cmake-dynamic", "cmake-static", "cmake-root",
            "cmake-targets", "sources", "ci", "deps", "configs",
            "presets", "docs",
        }
        assert set(COMPONENT_REGISTRY.keys()) == expected

    def test_generated_files_not_empty(self, target_dir):
        """No generated file should be empty."""
        generate(target_dir, policy=ConflictPolicy.OVERWRITE)
        for dirpath, _, filenames in os.walk(target_dir):
            for fname in filenames:
                fpath = Path(dirpath) / fname
                if ".tool" not in str(fpath):
                    assert fpath.stat().st_size > 0, f"Empty file: {fpath}"

    def test_cmake_targets_match_tool_toml(self, target_dir, ctx):
        """Generated lib/app files should match tool.toml declarations."""
        generate(target_dir, policy=ConflictPolicy.OVERWRITE)

        for lib in ctx.libs:
            lib_cmake = target_dir / "libs" / lib["name"] / "CMakeLists.txt"
            assert lib_cmake.exists(), f"Missing: {lib_cmake}"
            content = lib_cmake.read_text()
            assert lib["name"] in content

        for app in ctx.apps:
            app_cmake = target_dir / "apps" / app["name"] / "CMakeLists.txt"
            assert app_cmake.exists(), f"Missing: {app_cmake}"
            content = app_cmake.read_text()
            assert app["name"] in content

    def test_source_files_generated(self, target_dir, ctx):
        """C++ source files should be generated for all libs and apps."""
        generate(target_dir, policy=ConflictPolicy.OVERWRITE)

        for lib in ctx.libs:
            name = lib["name"]
            header = target_dir / "libs" / name / "include" / name / f"{name}.h"
            assert header.exists(), f"Missing header: {header}"
            assert "#pragma once" in header.read_text()

            lib_type = lib.get("type", "normal")
            if lib_type not in ("header-only", "interface"):
                src = target_dir / "libs" / name / "src" / f"{name}.cpp"
                assert src.exists(), f"Missing source: {src}"

            readme = target_dir / "libs" / name / "README.md"
            assert readme.exists(), f"Missing README: {readme}"

        for app in ctx.apps:
            main_cpp = target_dir / "apps" / app["name"] / "src" / "main.cpp"
            assert main_cpp.exists(), f"Missing main.cpp: {main_cpp}"

        assert (target_dir / "VERSION").exists()
        assert (target_dir / "README.md").exists()

    def test_dry_run_no_files(self, target_dir):
        """Dry run should not create any files."""
        result = generate(target_dir, policy=ConflictPolicy.OVERWRITE, dry_run=True)
        assert result.total > 0
        # No actual files should exist
        assert not (target_dir / "CMakeLists.txt").exists()
        assert not (target_dir / ".tool").exists()

    def test_generate_cli_initializes_git_for_new_target(self, tmp_path):
        """CLI generation should initialize git for a fresh target directory."""
        target = tmp_path / "fresh-project"
        generate_cmd.main(["--target-dir", str(target), "--force"])
        assert (target / ".git").exists()


class TestWizard:
    """Tests for the interactive project wizard."""

    def test_wizard_answers_to_config(self):
        """WizardAnswers should convert to a valid tool.toml config dict."""
        answers = WizardAnswers(
            name="MyProject",
            description="A cool project",
            author="Test Author",
            contact="test@example.com",
            license="Apache-2.0",
            cxx_standard="20",
            profile="library",
            libs=["core", "utils"],
            apps=[],
            features_without=["ci", "docker"],
        )
        cfg = answers.to_config()
        assert cfg["project"]["name"] == "MyProject"
        assert cfg["project"]["license"] == "Apache-2.0"
        assert cfg["project"]["cxx_standard"] == "20"
        assert cfg["generate"]["profile"] == "library"
        assert len(cfg["project"]["libs"]) == 2
        assert cfg["project"]["libs"][0]["name"] == "core"
        assert cfg["project"]["apps"] == []
        assert cfg["generate"]["without"] == ["ci", "docker"]

    def test_wizard_answers_default_profile_is_full(self):
        """Default profile should be 'full'."""
        answers = WizardAnswers(name="Proj")
        assert answers.profile == "full"

    def test_wizard_answers_with_apps(self):
        """Wizard should handle app declarations."""
        answers = WizardAnswers(
            name="AppProj",
            libs=["engine"],
            apps=["cli_tool"],
        )
        cfg = answers.to_config()
        assert len(cfg["project"]["apps"]) == 1
        assert cfg["project"]["apps"][0]["name"] == "cli_tool"
        assert cfg["project"]["apps"][0]["deps"] == ["engine"]

    def test_wizard_non_interactive_with_defaults(self):
        """Wizard with all defaults should produce a valid config."""
        wiz = Wizard(interactive=False)
        answers = wiz.run()
        cfg = answers.to_config()
        assert cfg["project"]["name"]
        assert cfg["generate"]["profile"] == "full"

    def test_wizard_config_generates_project(self, tmp_path):
        """Config from wizard answers should generate a valid project."""
        answers = WizardAnswers(
            name="WizardTest",
            description="Generated by wizard",
            author="Wizard",
            contact="wiz@example.com",
            license="MIT",
            cxx_standard="17",
            profile="full",
            libs=["core_lib"],
            apps=["main_app"],
        )
        cfg = answers.to_config()
        result = generate(tmp_path, policy=ConflictPolicy.OVERWRITE, config=cfg)
        assert len(result.errors) == 0
        assert (tmp_path / "CMakeLists.txt").exists()
        assert (tmp_path / "libs/core_lib/CMakeLists.txt").exists()
        assert (tmp_path / "apps/main_app/CMakeLists.txt").exists()


class TestMinimalSeedMode:
    """Prove that tool.toml + generator bootstraps a complete project."""

    def _seed_config(self) -> dict:
        """Return a minimal seed config for bootstrapping."""
        return {
            "project": {
                "name": "SeedProject",
                "version": "0.1.0",
                "description": "Seeded from tool.toml",
                "author": "seed-test",
                "contact": "seed@test.com",
                "license": "MIT",
                "cxx_standard": "17",
                "cmake_minimum": "3.25",
                "libs": [
                    {"name": "core", "type": "normal", "deps": [], "export": True},
                    {"name": "utils", "type": "normal", "deps": ["core"]},
                ],
                "apps": [
                    {"name": "main_app", "deps": ["core", "utils"], "gui": False},
                ],
                "tests": {"framework": "gtest", "fuzz": False, "auto_generate": True},
            },
            "cmake_modules": {
                "enabled": [
                    "CxxStandard", "ProjectConfigs", "ProjectOptions",
                    "BuildInfo", "Sanitizers", "Hardening", "FeatureFlags",
                    "LTO", "BuildCache",
                ],
            },
            "ci": {},
            "deps": {},
            "docker": {},
            "vscode": {},
            "git": {},
            "docs": {},
            "extension": {},
            "generate": {"on_conflict": "overwrite"},
            "build": {},
            "presets": {},
            "security": {},
            "hooks": {},
            "embedded": {},
            "gpu": {},
        }

    def test_seed_generates_complete_project(self, tmp_path):
        """A seed config should bootstrap a complete project tree."""
        cfg = self._seed_config()
        result = generate(tmp_path, policy=ConflictPolicy.OVERWRITE, config=cfg)
        assert len(result.errors) == 0
        assert result.total > 0

        # Root CMakeLists.txt
        root_cmake = tmp_path / "CMakeLists.txt"
        assert root_cmake.exists()
        root_content = root_cmake.read_text()
        assert "SeedProject" in root_content
        assert "cmake_minimum_required" in root_content

        # Libraries
        for lib_name in ("core", "utils"):
            lib_dir = tmp_path / "libs" / lib_name
            assert (lib_dir / "CMakeLists.txt").exists()
            assert (lib_dir / "include" / lib_name / f"{lib_name}.h").exists()
            assert (lib_dir / "src" / f"{lib_name}.cpp").exists()
            assert (lib_dir / "README.md").exists()

        # App
        app_dir = tmp_path / "apps" / "main_app"
        assert (app_dir / "CMakeLists.txt").exists()
        assert (app_dir / "src" / "main.cpp").exists()

        # Tests
        for lib_name in ("core", "utils"):
            test_file = (
                tmp_path / "tests" / "unit" / lib_name / f"{lib_name}_test.cpp"
            )
            assert test_file.exists()

        # CMakePresets.json
        assert (tmp_path / "CMakePresets.json").exists()

    def test_seed_dependency_wiring(self, tmp_path):
        """Generated project should reflect dependency relationships."""
        cfg = self._seed_config()
        generate(tmp_path, policy=ConflictPolicy.OVERWRITE, config=cfg)

        # utils depends on core
        utils_cmake = (tmp_path / "libs" / "utils" / "CMakeLists.txt").read_text()
        assert "core" in utils_cmake

        # main_app depends on core + utils
        app_cmake = (tmp_path / "apps" / "main_app" / "CMakeLists.txt").read_text()
        assert "core" in app_cmake
        assert "utils" in app_cmake

    def test_seed_idempotent(self, tmp_path):
        """Generating twice from the same seed should produce identical output."""
        cfg = self._seed_config()
        r1 = generate(tmp_path, policy=ConflictPolicy.OVERWRITE, config=cfg)
        r2 = generate(tmp_path, policy=ConflictPolicy.OVERWRITE, config=cfg)
        assert len(r2.errors) == 0
        # All files should be skipped (nothing changed)
        assert len(r2.created) == 0
        assert len(r2.written) == 0
        assert r2.total == r1.total

    def test_seed_incremental_skip(self, tmp_path):
        """Incremental mode with unchanged seed should skip everything."""
        cfg = self._seed_config()
        r1 = generate(tmp_path, policy=ConflictPolicy.OVERWRITE, config=cfg)
        r2 = generate(
            tmp_path, policy=ConflictPolicy.OVERWRITE, config=cfg,
            incremental=True,
        )
        assert len(r2.errors) == 0
        assert len(r2.created) == 0
        assert len(r2.written) == 0
        assert r2.total == r1.total

    def test_seed_profile_minimal(self, tmp_path):
        """Minimal profile should generate fewer components."""
        cfg = self._seed_config()
        cfg["generate"]["profile"] = "minimal"
        r_minimal = generate(tmp_path, policy=ConflictPolicy.OVERWRITE, config=cfg)
        assert len(r_minimal.errors) == 0

        # Second run with full profile in separate dir
        tmp_full = tmp_path.parent / "full_project"
        cfg_full = self._seed_config()
        r_full = generate(tmp_full, policy=ConflictPolicy.OVERWRITE, config=cfg_full)
        assert len(r_full.errors) == 0

        # Minimal should produce fewer files than full
        assert r_minimal.total < r_full.total
