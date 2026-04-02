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

from core.generator.engine import generate, build_context, COMPONENT_REGISTRY, GenerateResult
from core.generator.merge import ConflictPolicy


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
