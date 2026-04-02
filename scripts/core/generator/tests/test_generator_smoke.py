"""
Smoke tests for the generator — validates different project configurations.

Tests various tool.toml scenarios:
  - Minimal: single lib, single app
  - Full: all libs, all apps, fuzz, benchmarks
  - Header-only library
  - No tests
  - GUI app (Qt)
  - Fuzz-enabled project
  - Empty project (no libs, no apps)
  - Single app only (no libs)
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_scripts_dir = Path(__file__).resolve().parents[3]
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

from core.generator.engine import generate, build_context, ProjectContext
from core.generator.merge import ConflictPolicy


def _make_config(**overrides) -> dict:
    """Build a minimal tool.toml-style config dict with overrides."""
    base = {
        "project": {
            "name": "TestProject",
            "version": "0.1.0",
            "description": "Test",
            "author": "test",
            "contact": "",
            "license": "MIT",
            "cxx_standard": "17",
            "cmake_minimum": "3.25",
            "libs": [],
            "apps": [],
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
    for key, val in overrides.items():
        if "." in key:
            parts = key.split(".")
            d = base
            for p in parts[:-1]:
                d = d.setdefault(p, {})
            d[parts[-1]] = val
        else:
            base[key] = val
    return base


class TestSmokeScenarios:
    """Smoke tests for various project configurations."""

    def test_minimal_project(self, tmp_path):
        """Single lib + single app."""
        cfg = _make_config(
            **{
                "project.libs": [{"name": "mylib", "type": "normal", "deps": []}],
                "project.apps": [{"name": "myapp", "deps": ["mylib"], "gui": False}],
            }
        )
        result = generate(tmp_path, policy=ConflictPolicy.OVERWRITE, config=cfg)
        assert len(result.errors) == 0
        assert (tmp_path / "CMakeLists.txt").exists()
        assert (tmp_path / "libs/mylib/CMakeLists.txt").exists()
        assert (tmp_path / "apps/myapp/CMakeLists.txt").exists()
        assert (tmp_path / "tests/unit/mylib/CMakeLists.txt").exists()
        # Source files
        assert (tmp_path / "libs/mylib/include/mylib/mylib.h").exists()
        assert (tmp_path / "libs/mylib/src/mylib.cpp").exists()
        assert (tmp_path / "libs/mylib/README.md").exists()
        assert (tmp_path / "apps/myapp/src/main.cpp").exists()
        assert (tmp_path / "tests/unit/mylib/mylib_test.cpp").exists()
        assert (tmp_path / "VERSION").exists()
        assert (tmp_path / "README.md").exists()

    def test_full_project(self, tmp_path):
        """Multiple libs with all features."""
        cfg = _make_config(
            **{
                "project.libs": [
                    {"name": "core_lib", "type": "normal", "deps": [], "export": True, "benchmarks": True},
                    {"name": "fuzz_lib", "type": "normal", "deps": [], "fuzz": True},
                    {"name": "util_lib", "type": "normal", "deps": []},
                ],
                "project.apps": [
                    {"name": "main_app", "deps": ["core_lib"], "hardening": True, "build_info": True, "gui": False},
                    {"name": "gui_app", "deps": ["core_lib"], "gui": True, "qml": True},
                ],
                "project.tests": {"framework": "gtest", "fuzz": True, "auto_generate": True},
            }
        )
        result = generate(tmp_path, policy=ConflictPolicy.OVERWRITE, config=cfg)
        assert len(result.errors) == 0
        assert (tmp_path / "libs/core_lib/CMakeLists.txt").exists()
        assert (tmp_path / "libs/fuzz_lib/CMakeLists.txt").exists()
        assert (tmp_path / "apps/gui_app/CMakeLists.txt").exists()
        assert (tmp_path / "tests/fuzz/CMakeLists.txt").exists()

        # GUI app should have Qt guard
        gui_content = (tmp_path / "apps/gui_app/CMakeLists.txt").read_text()
        assert "ENABLE_QT" in gui_content

    def test_header_only_library(self, tmp_path):
        """Header-only library generates INTERFACE target."""
        cfg = _make_config(
            **{
                "project.libs": [{"name": "hdr_lib", "type": "header-only", "deps": []}],
                "project.apps": [],
            }
        )
        result = generate(tmp_path, policy=ConflictPolicy.OVERWRITE, config=cfg)
        assert len(result.errors) == 0
        content = (tmp_path / "libs/hdr_lib/CMakeLists.txt").read_text()
        assert "INTERFACE" in content
        assert "add_library(hdr_lib INTERFACE)" in content
        # Header-only: header but no source
        assert (tmp_path / "libs/hdr_lib/include/hdr_lib/hdr_lib.h").exists()
        assert not (tmp_path / "libs/hdr_lib/src/hdr_lib.cpp").exists()

    def test_no_tests(self, tmp_path):
        """Project without tests framework."""
        cfg = _make_config(
            **{
                "project.libs": [{"name": "simple", "type": "normal", "deps": []}],
                "project.apps": [{"name": "app", "deps": ["simple"], "gui": False}],
                "project.tests": {"framework": "", "fuzz": False, "auto_generate": False},
            }
        )
        result = generate(tmp_path, policy=ConflictPolicy.OVERWRITE, config=cfg)
        assert len(result.errors) == 0
        # Should not generate unit test files when auto_generate is False
        assert not (tmp_path / "tests/unit/simple/CMakeLists.txt").exists()

    def test_fuzz_project(self, tmp_path):
        """Fuzz-enabled project generates fuzz CMakeLists and harness."""
        cfg = _make_config(
            **{
                "project.libs": [{"name": "flib", "type": "normal", "deps": [], "fuzz": True}],
                "project.apps": [],
                "project.tests": {"framework": "gtest", "fuzz": True, "auto_generate": True},
            }
        )
        result = generate(tmp_path, policy=ConflictPolicy.OVERWRITE, config=cfg)
        assert len(result.errors) == 0
        fuzz_cmake = tmp_path / "tests/fuzz/CMakeLists.txt"
        assert fuzz_cmake.exists()
        content = fuzz_cmake.read_text()
        assert "fuzz_flib" in content
        # Fuzz harness source
        fuzz_src = tmp_path / "tests/fuzz/fuzz_flib.cpp"
        assert fuzz_src.exists()
        assert "LLVMFuzzerTestOneInput" in fuzz_src.read_text()

    def test_empty_project(self, tmp_path):
        """No libs, no apps — should still generate root cmake."""
        cfg = _make_config()
        result = generate(tmp_path, policy=ConflictPolicy.OVERWRITE, config=cfg)
        assert len(result.errors) == 0
        assert (tmp_path / "CMakeLists.txt").exists()
        assert (tmp_path / "cmake/ProjectConfigs.cmake").exists()

    def test_single_app_no_libs(self, tmp_path):
        """App without any libraries."""
        cfg = _make_config(
            **{
                "project.libs": [],
                "project.apps": [{"name": "solo_app", "deps": [], "gui": False}],
            }
        )
        result = generate(tmp_path, policy=ConflictPolicy.OVERWRITE, config=cfg)
        assert len(result.errors) == 0
        assert (tmp_path / "apps/solo_app/CMakeLists.txt").exists()

    def test_multiple_deps_app(self, tmp_path):
        """App linking multiple libraries."""
        cfg = _make_config(
            **{
                "project.libs": [
                    {"name": "lib_a", "type": "normal", "deps": []},
                    {"name": "lib_b", "type": "normal", "deps": ["lib_a"]},
                ],
                "project.apps": [{"name": "app", "deps": ["lib_a", "lib_b"], "gui": False}],
            }
        )
        result = generate(tmp_path, policy=ConflictPolicy.OVERWRITE, config=cfg)
        assert len(result.errors) == 0
        content = (tmp_path / "apps/app/CMakeLists.txt").read_text()
        assert "lib_a" in content
        assert "lib_b" in content

        # lib_b should depend on lib_a
        lib_b = (tmp_path / "libs/lib_b/CMakeLists.txt").read_text()
        assert "lib_a" in lib_b

    def test_blank_author_uses_git_fallback_in_license(self, tmp_path, monkeypatch):
        """Blank author should fall back to git config when generating LICENSE."""
        import subprocess

        def fake_run(cmd, **kwargs):
            text = kwargs.get("text", False)
            if cmd[:3] == ["git", "config", "user.name"]:
                return subprocess.CompletedProcess(cmd, 0, stdout="Template User\n" if text else b"Template User\n")
            if cmd[:3] == ["git", "config", "user.email"]:
                return subprocess.CompletedProcess(cmd, 0, stdout="template@example.com\n" if text else b"template@example.com\n")
            return subprocess.CompletedProcess(cmd, 1, stdout="" if text else b"")

        monkeypatch.setattr(subprocess, "run", fake_run)

        cfg = _make_config(**{"project.author": "", "project.contact": ""})
        result = generate(tmp_path, policy=ConflictPolicy.OVERWRITE, config=cfg)

        assert len(result.errors) == 0
        license_text = (tmp_path / "LICENSE").read_text()
        assert "Template User" in license_text
        assert "develooper1994" not in license_text

    def test_minimal_profile_skips_heavy_generated_artifacts(self, tmp_path):
        """Minimal profile should keep the generated repo lighter."""
        cfg = _make_config(**{"generate.profile": "minimal"})
        result = generate(tmp_path, policy=ConflictPolicy.OVERWRITE, config=cfg)

        assert len(result.errors) == 0
        assert not (tmp_path / "extension/package.json").exists()
        assert not (tmp_path / "docker/Dockerfile").exists()

    def test_library_profile_skips_app_scaffolding(self, tmp_path):
        """Library profile should omit app entrypoints to keep the repo focused."""
        cfg = _make_config(
            **{
                "generate.profile": "library",
                "project.libs": [{"name": "core_only", "type": "normal", "deps": []}],
                "project.apps": [{"name": "demo_app", "deps": ["core_only"], "gui": False}],
            }
        )
        result = generate(tmp_path, policy=ConflictPolicy.OVERWRITE, config=cfg)

        assert len(result.errors) == 0
        assert (tmp_path / "libs/core_only/CMakeLists.txt").exists()
        assert not (tmp_path / "apps/demo_app/src/main.cpp").exists()

    def test_without_features_can_disable_ci_and_vscode(self, tmp_path):
        """Feature toggles should allow opting out of CI and editor metadata."""
        cfg = _make_config(**{"generate.without": ["ci", "vscode"]})
        result = generate(tmp_path, policy=ConflictPolicy.OVERWRITE, config=cfg)

        assert len(result.errors) == 0
        assert not (tmp_path / ".github/workflows/ci.yml").exists()
        assert not (tmp_path / ".vscode/settings.json").exists()

    def test_app_profile_disables_extension(self, tmp_path):
        """App profile should disable extension generation but keep CI."""
        cfg = _make_config(
            **{
                "generate.profile": "app",
                "project.libs": [{"name": "svc", "type": "normal", "deps": []}],
                "project.apps": [{"name": "runner", "deps": ["svc"], "gui": False}],
            }
        )
        result = generate(tmp_path, policy=ConflictPolicy.OVERWRITE, config=cfg)
        assert len(result.errors) == 0
        # App profile should keep apps and libs
        assert (tmp_path / "libs/svc/CMakeLists.txt").exists()
        assert (tmp_path / "apps/runner/CMakeLists.txt").exists()
        # Extension should be disabled by default for app profile
        assert not (tmp_path / "extension/package.json").exists()

    def test_embedded_profile_keeps_libs_disables_extension(self, tmp_path):
        """Embedded profile should keep static libs, omit extension."""
        cfg = _make_config(
            **{
                "generate.profile": "embedded",
                "project.libs": [{"name": "driver", "type": "normal", "deps": []}],
                "project.apps": [{"name": "firmware", "deps": ["driver"], "gui": False}],
            }
        )
        result = generate(tmp_path, policy=ConflictPolicy.OVERWRITE, config=cfg)
        assert len(result.errors) == 0
        assert (tmp_path / "libs/driver/CMakeLists.txt").exists()
        assert (tmp_path / "apps/firmware/CMakeLists.txt").exists()
        assert not (tmp_path / "extension/package.json").exists()
