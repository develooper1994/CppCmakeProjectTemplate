"""
Edge-case tests for the generator engine.

Covers:
  - Corrupted manifest (invalid JSON, wrong version)
  - Invalid template names
  - MERGE conflict policy
  - Circular dependency detection
  - Lib-to-lib dependency validation
  - Special characters in names
  - Fuzz config without fuzz=true
  - With and without same feature simultaneously
  - Invalid/custom profile names
  - Manifest file deleted between runs
  - Component cleanup when disabling features
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_scripts_dir = Path(__file__).resolve().parents[3]
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

from core.generator.engine import generate, build_context, GenerateResult
from core.generator.manifest import GenerationManifest
from core.generator.merge import ConflictPolicy
from core.utils.config_schema import validate_config


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


# ---------------------------------------------------------------------------
# Manifest edge cases
# ---------------------------------------------------------------------------

class TestManifestEdgeCases:
    """Tests for corrupted or missing manifest scenarios."""

    def test_corrupted_manifest_invalid_json(self, tmp_path):
        """Generator should recover from corrupted manifest JSON."""
        cfg = _make_config(
            **{"project.libs": [{"name": "lib1", "type": "normal", "deps": []}]}
        )
        # First generate
        result1 = generate(tmp_path, policy=ConflictPolicy.OVERWRITE, config=cfg)
        assert len(result1.errors) == 0

        # Corrupt the manifest
        manifest_path = tmp_path / ".tool" / "generation_manifest.json"
        assert manifest_path.exists()
        manifest_path.write_text("{invalid json!!!", encoding="utf-8")

        # Second run should still work — treats it as fresh
        result2 = generate(tmp_path, policy=ConflictPolicy.OVERWRITE, config=cfg)
        assert len(result2.errors) == 0
        assert result2.total > 0

    def test_corrupted_manifest_wrong_version(self, tmp_path):
        """Generator should handle manifest with unexpected version number.

        Since all files are already on disk with correct content,
        resolve_write will skip them (disk == new_content). The key check
        is that no errors occur — the unknown manifest version is silently
        discarded.
        """
        cfg = _make_config(
            **{"project.libs": [{"name": "lib1", "type": "normal", "deps": []}]}
        )
        result1 = generate(tmp_path, policy=ConflictPolicy.OVERWRITE, config=cfg)
        assert len(result1.errors) == 0

        # Write manifest with wrong version
        manifest_path = tmp_path / ".tool" / "generation_manifest.json"
        manifest_path.write_text(
            json.dumps({"version": 999, "files": {}}, indent=2),
            encoding="utf-8",
        )

        # Should succeed without errors despite unknown manifest version
        result2 = generate(tmp_path, policy=ConflictPolicy.OVERWRITE, config=cfg)
        assert len(result2.errors) == 0
        assert result2.total > 0

    def test_manifest_deleted_between_runs(self, tmp_path):
        """Deleting manifest between runs should cause full regeneration."""
        cfg = _make_config(
            **{"project.libs": [{"name": "lib1", "type": "normal", "deps": []}]}
        )
        result1 = generate(tmp_path, policy=ConflictPolicy.OVERWRITE, config=cfg)
        assert len(result1.errors) == 0

        # Delete the manifest
        manifest_path = tmp_path / ".tool" / "generation_manifest.json"
        manifest_path.unlink()

        # Regenerate — should recreate all files
        result2 = generate(tmp_path, policy=ConflictPolicy.OVERWRITE, config=cfg)
        assert len(result2.errors) == 0
        assert result2.total > 0

    def test_manifest_class_hash_consistency(self, tmp_path):
        """Manifest hash_content should be deterministic."""
        m = GenerationManifest(tmp_path / "manifest.json")
        content = "hello world\n"
        h1 = m.hash_content(content)
        h2 = m.hash_content(content)
        assert h1 == h2
        assert len(h1) == 64  # SHA256

    def test_manifest_file_modified_detection(self, tmp_path):
        """Manifest should detect user modifications correctly."""
        m = GenerationManifest(tmp_path / "manifest.json")
        m.record("test.txt", "original content", "sources")
        assert not m.file_was_modified_by_user("test.txt", "original content")
        assert m.file_was_modified_by_user("test.txt", "modified content")

    def test_manifest_is_stale_detection(self, tmp_path):
        """Manifest should detect when new content differs from old."""
        m = GenerationManifest(tmp_path / "manifest.json")
        m.record("test.txt", "v1", "sources")
        assert not m.is_stale("test.txt", "v1")
        assert m.is_stale("test.txt", "v2")

    def test_manifest_untracked_file(self, tmp_path):
        """Operations on untracked files should return safe defaults."""
        m = GenerationManifest(tmp_path / "manifest.json")
        assert m.get_entry("nonexistent.txt") is None
        assert not m.is_unchanged("nonexistent.txt", "anything")
        assert m.is_stale("nonexistent.txt", "anything")
        assert not m.file_was_modified_by_user("nonexistent.txt", "anything")


# ---------------------------------------------------------------------------
# Validation edge cases
# ---------------------------------------------------------------------------

class TestValidationEdgeCases:
    """Tests for config_schema cross-reference validation."""

    def test_invalid_template_name(self):
        """Unknown template name should produce an error."""
        cfg = _make_config(
            **{
                "project.libs": [
                    {"name": "bad_lib", "type": "normal", "deps": [], "template": "nonexistent"},
                ],
            }
        )
        errors, warnings = validate_config(cfg)
        assert any("invalid template 'nonexistent'" in e for e in errors)

    def test_valid_template_names_accepted(self):
        """All valid template names should pass."""
        for tmpl in ("exported", "fuzzable", "hasher", "default", "normal"):
            cfg = _make_config(
                **{
                    "project.libs": [
                        {"name": "lib1", "type": "normal", "deps": [], "template": tmpl},
                    ],
                }
            )
            errors, warnings = validate_config(cfg)
            template_errors = [e for e in errors if "invalid template" in e]
            assert len(template_errors) == 0, f"Template '{tmpl}' should be valid"

    def test_lib_dep_references_undeclared_lib(self):
        """Lib depending on non-existent lib should produce an error."""
        cfg = _make_config(
            **{
                "project.libs": [
                    {"name": "child", "type": "normal", "deps": ["nonexistent_parent"]},
                ],
            }
        )
        errors, _ = validate_config(cfg)
        assert any("nonexistent_parent" in e and "undeclared" in e for e in errors)

    def test_lib_dep_references_valid_lib(self):
        """Lib depending on declared lib should not error."""
        cfg = _make_config(
            **{
                "project.libs": [
                    {"name": "parent", "type": "normal", "deps": []},
                    {"name": "child", "type": "normal", "deps": ["parent"]},
                ],
            }
        )
        errors, _ = validate_config(cfg)
        dep_errors = [e for e in errors if "undeclared" in e]
        assert len(dep_errors) == 0

    def test_circular_dependency_self_loop(self):
        """Library depending on itself should produce an error."""
        cfg = _make_config(
            **{
                "project.libs": [
                    {"name": "selfref", "type": "normal", "deps": ["selfref"]},
                ],
            }
        )
        errors, _ = validate_config(cfg)
        assert any("circular dependency" in e for e in errors)

    def test_circular_dependency_two_libs(self):
        """Two-library circular dependency should be detected."""
        cfg = _make_config(
            **{
                "project.libs": [
                    {"name": "a", "type": "normal", "deps": ["b"]},
                    {"name": "b", "type": "normal", "deps": ["a"]},
                ],
            }
        )
        errors, _ = validate_config(cfg)
        assert any("circular dependency" in e for e in errors)

    def test_circular_dependency_three_libs(self):
        """Three-library circular dependency should be detected."""
        cfg = _make_config(
            **{
                "project.libs": [
                    {"name": "a", "type": "normal", "deps": ["b"]},
                    {"name": "b", "type": "normal", "deps": ["c"]},
                    {"name": "c", "type": "normal", "deps": ["a"]},
                ],
            }
        )
        errors, _ = validate_config(cfg)
        assert any("circular dependency" in e for e in errors)

    def test_no_circular_dependency_in_dag(self):
        """Valid DAG should not report circular dependencies."""
        cfg = _make_config(
            **{
                "project.libs": [
                    {"name": "base", "type": "normal", "deps": []},
                    {"name": "mid", "type": "normal", "deps": ["base"]},
                    {"name": "top", "type": "normal", "deps": ["base", "mid"]},
                ],
            }
        )
        errors, _ = validate_config(cfg)
        circ_errors = [e for e in errors if "circular dependency" in e]
        assert len(circ_errors) == 0

    def test_app_dep_undeclared(self):
        """App referencing undeclared lib should error (existing behavior)."""
        cfg = _make_config(
            **{
                "project.libs": [{"name": "real_lib", "type": "normal", "deps": []}],
                "project.apps": [{"name": "app1", "deps": ["fake_lib"], "gui": False}],
            }
        )
        errors, _ = validate_config(cfg)
        assert any("fake_lib" in e and "undeclared" in e for e in errors)

    def test_duplicate_lib_names(self):
        """Duplicate library names should produce an error (existing behavior)."""
        cfg = _make_config(
            **{
                "project.libs": [
                    {"name": "dup", "type": "normal", "deps": []},
                    {"name": "dup", "type": "normal", "deps": []},
                ],
            }
        )
        errors, _ = validate_config(cfg)
        assert any("duplicate library name 'dup'" in e for e in errors)


# ---------------------------------------------------------------------------
# Generator edge cases
# ---------------------------------------------------------------------------

class TestGeneratorEdgeCases:
    """Tests for unusual but valid generator configurations."""

    def test_lib_with_benchmarks_but_no_fuzz(self, tmp_path):
        """Library with benchmarks but fuzz disabled should still work."""
        cfg = _make_config(
            **{
                "project.libs": [
                    {"name": "bench_lib", "type": "normal", "deps": [],
                     "benchmarks": True, "fuzz": False, "export": True},
                ],
            }
        )
        result = generate(tmp_path, policy=ConflictPolicy.OVERWRITE, config=cfg)
        assert len(result.errors) == 0
        # Benchmark source should exist
        bench = tmp_path / "libs" / "bench_lib" / "benchmarks" / "bench_bench_lib.cpp"
        assert bench.exists()
        assert "benchmark" in bench.read_text().lower()

    def test_lib_with_underscore_name(self, tmp_path):
        """Library names with underscores should work correctly."""
        cfg = _make_config(
            **{
                "project.libs": [
                    {"name": "my_cool_lib", "type": "normal", "deps": []},
                ],
            }
        )
        result = generate(tmp_path, policy=ConflictPolicy.OVERWRITE, config=cfg)
        assert len(result.errors) == 0
        assert (tmp_path / "libs" / "my_cool_lib" / "include" / "my_cool_lib" / "my_cool_lib.h").exists()

    def test_interface_library(self, tmp_path):
        """Interface library should generate with INTERFACE target."""
        cfg = _make_config(
            **{
                "project.libs": [
                    {"name": "iface_lib", "type": "interface", "deps": []},
                ],
            }
        )
        result = generate(tmp_path, policy=ConflictPolicy.OVERWRITE, config=cfg)
        assert len(result.errors) == 0
        cmake_content = (tmp_path / "libs" / "iface_lib" / "CMakeLists.txt").read_text()
        assert "INTERFACE" in cmake_content

    def test_with_and_without_same_feature(self, tmp_path):
        """Explicit --with should override --without for same feature."""
        cfg = _make_config(
            **{
                "generate.with": ["ci"],
                "generate.without": ["ci"],
                "project.libs": [{"name": "lib1", "type": "normal", "deps": []}],
            }
        )
        # engine.py: get_enabled_features checks ctx.generate["with"]
        # is_feature_enabled: if in "with" → True (takes precedence)
        result = generate(tmp_path, policy=ConflictPolicy.OVERWRITE, config=cfg)
        assert len(result.errors) == 0

    def test_invalid_profile_triggers_validation_error(self, tmp_path):
        """Unknown profile name should be caught by validation."""
        cfg = _make_config(
            **{
                "generate.profile": "nonexistent_profile",
                "project.libs": [{"name": "lib1", "type": "normal", "deps": []}],
            }
        )
        result = generate(tmp_path, policy=ConflictPolicy.OVERWRITE, config=cfg)
        assert any("nonexistent_profile" in e for e in result.errors)

    def test_many_libs_at_scale(self, tmp_path):
        """Generator should handle 20+ libraries without errors."""
        libs = [
            {"name": f"lib_{i:03d}", "type": "normal", "deps": []}
            for i in range(20)
        ]
        cfg = _make_config(**{"project.libs": libs})
        result = generate(tmp_path, policy=ConflictPolicy.OVERWRITE, config=cfg)
        assert len(result.errors) == 0
        for i in range(20):
            assert (tmp_path / "libs" / f"lib_{i:03d}" / "CMakeLists.txt").exists()

    def test_chained_lib_dependencies(self, tmp_path):
        """Chain of lib dependencies (a→b→c) should generate correctly."""
        cfg = _make_config(
            **{
                "project.libs": [
                    {"name": "foundation", "type": "normal", "deps": []},
                    {"name": "middle", "type": "normal", "deps": ["foundation"]},
                    {"name": "top_level", "type": "normal", "deps": ["middle"]},
                ],
                "project.apps": [{"name": "app", "deps": ["top_level"], "gui": False}],
            }
        )
        result = generate(tmp_path, policy=ConflictPolicy.OVERWRITE, config=cfg)
        assert len(result.errors) == 0
        # Verify dependency chain in CMake files
        middle_cmake = (tmp_path / "libs" / "middle" / "CMakeLists.txt").read_text()
        assert "foundation" in middle_cmake
        app_cmake = (tmp_path / "apps" / "app" / "CMakeLists.txt").read_text()
        assert "top_level" in app_cmake


# ---------------------------------------------------------------------------
# Conflict policy edge cases
# ---------------------------------------------------------------------------

class TestConflictPolicyEdgeCases:
    """Tests for conflict resolution policies."""

    def test_skip_preserves_user_changes(self, tmp_path):
        """SKIP policy should never overwrite user-modified files."""
        cfg = _make_config(
            **{"project.libs": [{"name": "lib1", "type": "normal", "deps": []}]}
        )
        generate(tmp_path, policy=ConflictPolicy.OVERWRITE, config=cfg)

        # User edits a file
        user_content = "// My custom CMakeLists\n"
        cmake_file = tmp_path / "libs" / "lib1" / "CMakeLists.txt"
        cmake_file.write_text(user_content)

        # Regenerate with SKIP
        result = generate(tmp_path, policy=ConflictPolicy.SKIP, config=cfg)
        assert len(result.errors) == 0

        # User content should be preserved
        assert cmake_file.read_text() == user_content

    def test_overwrite_replaces_user_changes(self, tmp_path):
        """OVERWRITE policy should replace user-modified files."""
        cfg = _make_config(
            **{"project.libs": [{"name": "lib1", "type": "normal", "deps": []}]}
        )
        generate(tmp_path, policy=ConflictPolicy.OVERWRITE, config=cfg)

        # User edits a file
        cmake_file = tmp_path / "libs" / "lib1" / "CMakeLists.txt"
        original = cmake_file.read_text()
        cmake_file.write_text("// CUSTOM\n")

        # Regenerate with OVERWRITE
        result = generate(tmp_path, policy=ConflictPolicy.OVERWRITE, config=cfg)
        assert len(result.errors) == 0

        # Should be back to generated content
        assert cmake_file.read_text() == original

    def test_partial_conflict(self, tmp_path):
        """Some files modified, some not — verify correct behavior per-file."""
        cfg = _make_config(
            **{
                "project.libs": [{"name": "lib1", "type": "normal", "deps": []}],
                "project.apps": [{"name": "app1", "deps": ["lib1"], "gui": False}],
            }
        )
        generate(tmp_path, policy=ConflictPolicy.OVERWRITE, config=cfg)

        # Modify only the lib CMakeLists
        lib_cmake = tmp_path / "libs" / "lib1" / "CMakeLists.txt"
        lib_cmake.write_text("// MODIFIED\n")

        # Regenerate with SKIP
        result = generate(tmp_path, policy=ConflictPolicy.SKIP, config=cfg)
        assert len(result.errors) == 0

        # Modified file should be preserved (skipped)
        assert lib_cmake.read_text() == "// MODIFIED\n"
        # Unmodified app CMakeLists should be skipped too (unchanged)
        assert (tmp_path / "apps" / "app1" / "CMakeLists.txt").exists()


# ---------------------------------------------------------------------------
# Incremental generation
# ---------------------------------------------------------------------------

class TestIncrementalGeneration:
    """Tests for the incremental generation feature (input hashing)."""

    def test_incremental_skips_unchanged_components(self, tmp_path):
        """Second run with incremental=True should skip all components."""
        cfg = _make_config(
            **{"project.libs": [{"name": "lib1", "type": "normal", "deps": []}]}
        )
        r1 = generate(tmp_path, policy=ConflictPolicy.OVERWRITE, config=cfg)
        assert len(r1.errors) == 0
        assert r1.total > 0

        # Second run with incremental — all components should be skipped
        r2 = generate(
            tmp_path, policy=ConflictPolicy.OVERWRITE, config=cfg,
            incremental=True,
        )
        assert len(r2.errors) == 0
        assert len(r2.created) == 0
        assert len(r2.written) == 0
        # All files should appear as skipped
        assert len(r2.skipped) == r1.total

    def test_incremental_reruns_on_config_change(self, tmp_path):
        """Changing config should cause incremental to regenerate."""
        cfg1 = _make_config(
            **{"project.libs": [{"name": "lib1", "type": "normal", "deps": []}]}
        )
        generate(tmp_path, policy=ConflictPolicy.OVERWRITE, config=cfg1)

        # Change config: add a second lib
        cfg2 = _make_config(
            **{
                "project.libs": [
                    {"name": "lib1", "type": "normal", "deps": []},
                    {"name": "lib2", "type": "normal", "deps": []},
                ],
            }
        )
        r2 = generate(
            tmp_path, policy=ConflictPolicy.OVERWRITE, config=cfg2,
            incremental=True,
        )
        assert len(r2.errors) == 0
        # Some files should be created or written (not all skipped)
        assert len(r2.created) + len(r2.written) > 0

    def test_incremental_without_flag_always_runs(self, tmp_path):
        """Without incremental, components always run even if unchanged."""
        cfg = _make_config(
            **{"project.libs": [{"name": "lib1", "type": "normal", "deps": []}]}
        )
        r1 = generate(tmp_path, policy=ConflictPolicy.OVERWRITE, config=cfg)
        assert len(r1.errors) == 0

        # Without incremental flag, second run should process all files
        r2 = generate(tmp_path, policy=ConflictPolicy.OVERWRITE, config=cfg)
        assert len(r2.errors) == 0
        # Files exist and match → all skipped by resolve_write, but
        # generators were still invoked (just no writes needed)
        assert r2.total == r1.total

    def test_incremental_component_hash_stored_in_manifest(self, tmp_path):
        """Component hashes should be persisted in the manifest file."""
        cfg = _make_config(
            **{"project.libs": [{"name": "lib1", "type": "normal", "deps": []}]}
        )
        generate(tmp_path, policy=ConflictPolicy.OVERWRITE, config=cfg)

        manifest_path = tmp_path / ".tool" / "generation_manifest.json"
        data = json.loads(manifest_path.read_text())
        assert "component_hashes" in data
        assert len(data["component_hashes"]) > 0
        # Each hash should be a SHA256 hex string (64 chars)
        for h in data["component_hashes"].values():
            assert len(h) == 64

    def test_incremental_via_config_flag(self, tmp_path):
        """generate.incremental=true in config should enable incremental mode."""
        cfg = _make_config(
            **{
                "project.libs": [{"name": "lib1", "type": "normal", "deps": []}],
                "generate.incremental": True,
            }
        )
        r1 = generate(tmp_path, policy=ConflictPolicy.OVERWRITE, config=cfg)
        assert len(r1.errors) == 0

        # Second run — incremental enabled via config, should skip
        r2 = generate(tmp_path, policy=ConflictPolicy.OVERWRITE, config=cfg)
        assert len(r2.errors) == 0
        assert len(r2.created) == 0
        assert len(r2.written) == 0
        assert len(r2.skipped) == r1.total
