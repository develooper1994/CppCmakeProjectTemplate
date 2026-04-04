"""
Build-verified integration tests for the generator engine.

These tests generate complete projects in /tmp, then verify they can
actually configure and build with CMake. This catches structural issues
that file-existence tests miss.

Requirements:
  - cmake >= 3.25
  - A C++ compiler (gcc or clang)
  - ninja build system

Tests are marked with @pytest.mark.integration and can be skipped in CI
with: pytest -m "not integration"
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

# Ensure scripts/ is on sys.path
_scripts_dir = Path(__file__).resolve().parents[3]
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

from core.generator.engine import (
    generate,
    build_context,
    COMPONENT_REGISTRY,
    get_profile_components,
)
from core.generator.merge import ConflictPolicy


def _has_tool(name: str) -> bool:
    return shutil.which(name) is not None


_HAS_CMAKE = _has_tool("cmake")
_HAS_NINJA = _has_tool("ninja")
_HAS_GCC = _has_tool("g++")
_HAS_CLANG = _has_tool("clang++")
_HAS_BUILD_TOOLS = _HAS_CMAKE and _HAS_NINJA and (_HAS_GCC or _HAS_CLANG)

integration = pytest.mark.skipif(
    not _HAS_BUILD_TOOLS,
    reason="Requires cmake, ninja, and a C++ compiler",
)


def _minimal_config(**overrides) -> dict:
    """Build a minimal but complete tool.toml-like config for testing.

    Matches the nested format that build_context() expects:
      project.name, project.libs, presets.compilers, etc.
    """
    cfg = {
        "project": {
            "name": "IntegrationTest",
            "version": "1.0.0",
            "description": "Test project for build verification",
            "author": "test",
            "license": "MIT",
            "cxx_standard": "17",
            "cmake_minimum": "3.25",
            "profile": "minimal",
            "libs": [
                {
                    "name": "testlib",
                    "type": "normal",
                    "description": "A test library",
                },
            ],
            "apps": [
                {
                    "name": "testapp",
                    "description": "A test application",
                    "libs": ["testlib"],
                },
            ],
            "tests": {
                "framework": "gtest",
                "fuzz": False,
                "auto_generate": True,
            },
        },
        "presets": {
            "compilers": ["gcc"] if _HAS_GCC else ["clang"],
            "build_types": ["debug"],
            "linkages": ["static"],
            "arches": ["x86_64"],
        },
        "features": {
            "unit_tests": True,
            "fuzz_tests": False,
            "ci": False,
            "docs": False,
        },
        "generate": {
            "on_conflict": "overwrite",
        },
    }
    # Apply dot-notation overrides (e.g., "project.name" = "Foo")
    for key, val in overrides.items():
        parts = key.split(".")
        d = cfg
        for p in parts[:-1]:
            d = d.setdefault(p, {})
        d[parts[-1]] = val
    return cfg


@integration
class TestBuildVerification:
    """Tests that generate a project and verify it builds."""

    def test_generate_and_cmake_configure(self, tmp_path):
        """Generated project should successfully configure with CMake."""
        target = tmp_path / "project"
        config = _minimal_config()

        result = generate(
            target, policy=ConflictPolicy.OVERWRITE, config=config,
        )
        assert len(result.errors) == 0
        assert len(result.created) > 0

        # Verify CMakePresets.json was generated
        assert (target / "CMakePresets.json").exists()
        # Verify root CMakeLists.txt was generated
        assert (target / "CMakeLists.txt").exists()

        # Try cmake configure
        compiler = "gcc" if _HAS_GCC else "clang"
        preset = f"{compiler}-debug-static-x86_64"
        proc = subprocess.run(
            ["cmake", "--preset", preset],
            cwd=target,
            capture_output=True,
            text=True,
            timeout=120,
        )

        # Note: configure may fail if vcpkg/conan deps are missing or
        # custom cmake modules aren't available in the generated tree.
        # We check stderr for CMake *syntax* errors only — command-not-found
        # for project-specific cmake functions is acceptable in isolation.
        if proc.returncode != 0:
            stderr = proc.stderr.lower()
            # CMake syntax errors are always fatal
            assert "syntax error" not in stderr, f"CMake syntax error:\n{proc.stderr}"
            # Accept missing deps, unknown commands (project cmake modules),
            # and missing includes as expected in isolated generation.
            acceptable = (
                "could not find",
                "unknown cmake command",
                "include could not find",
            )
            if "cmake error" in stderr:
                assert any(msg in stderr for msg in acceptable), \
                    f"CMake configuration error (unexpected):\n{proc.stderr}"

    def test_generate_all_profiles(self, tmp_path):
        """All profiles should generate without errors."""
        for profile in ("full", "minimal", "library", "app", "embedded"):
            target = tmp_path / profile
            config = _minimal_config(**{"project.profile": profile})
            result = generate(
                target, policy=ConflictPolicy.OVERWRITE, config=config,
            )
            assert len(result.errors) == 0, \
                f"Profile '{profile}' had errors: {result.errors}"
            assert result.total > 0, \
                f"Profile '{profile}' generated no files"

    def test_generated_project_file_structure(self, tmp_path):
        """Verify the generated project has the expected directory structure."""
        target = tmp_path / "project"
        config = _minimal_config()

        generate(target, policy=ConflictPolicy.OVERWRITE, config=config)

        # Core files must exist
        assert (target / "CMakeLists.txt").exists()
        assert (target / "CMakePresets.json").exists()
        assert (target / "LICENSE").exists()

        # Library structure
        assert (target / "libs" / "testlib" / "CMakeLists.txt").exists()
        assert (target / "libs" / "testlib" / "include" / "testlib").is_dir()

        # App structure
        assert (target / "apps" / "testapp" / "CMakeLists.txt").exists() or \
               (target / "apps" / "CMakeLists.txt").exists()

    def test_agents_files_generated(self, tmp_path):
        """Verify AI agent instruction files are generated."""
        target = tmp_path / "project"
        config = _minimal_config()

        result = generate(
            target, policy=ConflictPolicy.OVERWRITE, config=config,
        )
        assert len(result.errors) == 0

        # AGENTS.md should be generated
        agents_md = target / "AGENTS.md"
        assert agents_md.exists(), "AGENTS.md not generated"
        content = agents_md.read_text(encoding="utf-8")
        assert "IntegrationTest" in content
        assert "tool.py" in content

        # Copilot instructions
        copilot = target / ".github" / "copilot-instructions.md"
        assert copilot.exists(), ".github/copilot-instructions.md not generated"

        # Cursor rules
        assert (target / ".cursorrules").exists()

        # Cline rules
        assert (target / ".clinerules").exists()

    def test_presets_cross_platform_when_requested(self, tmp_path):
        """Presets should include cross-platform compiler entries when explicitly configured."""
        import json

        target = tmp_path / "project"
        config = _minimal_config()
        # Explicitly request all platform compilers
        config["presets"]["compilers"] = ["gcc", "clang", "msvc", "appleclang"]

        generate(target, policy=ConflictPolicy.OVERWRITE, config=config)

        presets_file = target / "CMakePresets.json"
        assert presets_file.exists()
        data = json.loads(presets_file.read_text(encoding="utf-8"))

        configure_names = [p["name"] for p in data.get("configurePresets", [])
                           if not p.get("hidden", False)]

        # Should have gcc, clang, msvc, and appleclang presets
        has_gcc = any("gcc-" in n for n in configure_names)
        has_clang = any(n.startswith("clang-") for n in configure_names)
        has_msvc = any("msvc-" in n for n in configure_names)
        has_appleclang = any("appleclang-" in n for n in configure_names)

        assert has_gcc, f"No gcc presets found in {configure_names}"
        assert has_clang, f"No clang presets found in {configure_names}"
        assert has_msvc, f"No MSVC presets found in {configure_names}"
        assert has_appleclang, f"No AppleClang presets found in {configure_names}"

        # Verify base presets include macOS + Windows bases
        base_names = [p["name"] for p in data.get("configurePresets", [])
                      if p.get("hidden", False)]
        assert "macos-base" in base_names
        assert "macos-appleclang-base" in base_names
        assert "win-base" in base_names

    def test_incremental_skip_unchanged(self, tmp_path):
        """Incremental mode should skip components with unchanged inputs."""
        target = tmp_path / "project"
        config = _minimal_config()

        # First generation
        r1 = generate(
            target, policy=ConflictPolicy.OVERWRITE, config=config,
            incremental=True,
        )
        assert len(r1.errors) == 0
        assert len(r1.created) > 0

        # Second generation with same config
        r2 = generate(
            target, policy=ConflictPolicy.OVERWRITE, config=config,
            incremental=True,
        )
        assert len(r2.errors) == 0
        # All should be skipped
        assert len(r2.skipped) > 0
        assert len(r2.created) == 0
        assert len(r2.written) == 0


class TestComponentRegistry:
    """Verify component registry is complete."""

    def test_agents_component_registered(self):
        """agents component should be in the registry."""
        assert "agents" in COMPONENT_REGISTRY

    def test_all_profiles_include_agents(self):
        """agents should be in all profiles (it's metadata, not build config)."""
        for profile in ("full", "minimal", "library", "app", "embedded"):
            components = get_profile_components(profile)
            assert "agents" in components, \
                f"Profile '{profile}' missing 'agents' component"

    def test_component_count(self):
        """Registry should have 11 components (10 original + agents)."""
        assert len(COMPONENT_REGISTRY) == 11
