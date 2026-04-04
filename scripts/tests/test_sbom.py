"""
Tests for core/commands/sbom.py — SBOM generation (SPDX / CycloneDX)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))


@pytest.fixture
def sbom_workspace(tmp_path, monkeypatch):
    """Workspace with vcpkg.json, conanfile.py, and requirements-dev.txt."""
    (tmp_path / "VERSION").write_text("1.0.0\n", encoding="utf-8")
    (tmp_path / "CMakeLists.txt").write_text(
        "project(SbomProject VERSION 1.0.0 LANGUAGES CXX)\n",
        encoding="utf-8",
    )
    (tmp_path / "vcpkg.json").write_text(json.dumps({
        "dependencies": ["fmt", {"name": "spdlog", "version>=": "1.12.0"}]
    }), encoding="utf-8")
    (tmp_path / "conanfile.py").write_text(
        'class Pkg:\n'
        '    def requirements(self):\n'
        '        self.requires("gtest/1.14.0")\n'
        '        self.requires("nlohmann_json/3.11.3")\n',
        encoding="utf-8",
    )
    (tmp_path / "requirements-dev.txt").write_text(
        "pytest>=7.0\nblack==23.1.0\n# comment\n",
        encoding="utf-8",
    )
    import core.commands.sbom as sbom_mod
    monkeypatch.setattr(sbom_mod, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(sbom_mod, "get_project_name", lambda: "SbomProject")
    monkeypatch.setattr(sbom_mod, "get_project_version", lambda: "1.0.0")
    return tmp_path


@pytest.fixture
def empty_workspace(tmp_path, monkeypatch):
    """Workspace with no dependency files."""
    (tmp_path / "VERSION").write_text("0.1.0\n", encoding="utf-8")
    (tmp_path / "CMakeLists.txt").write_text(
        "project(EmptyProject VERSION 0.1.0 LANGUAGES CXX)\n",
        encoding="utf-8",
    )
    import core.commands.sbom as sbom_mod
    monkeypatch.setattr(sbom_mod, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(sbom_mod, "get_project_name", lambda: "EmptyProject")
    monkeypatch.setattr(sbom_mod, "get_project_version", lambda: "0.1.0")
    return tmp_path


class TestDetectDependencies:
    def test_detects_vcpkg_deps(self, sbom_workspace):
        from core.commands.sbom import _detect_dependencies
        deps = _detect_dependencies()
        vcpkg_deps = [d for d in deps if d["source"] == "vcpkg"]
        assert len(vcpkg_deps) == 2
        names = {d["name"] for d in vcpkg_deps}
        assert "fmt" in names
        assert "spdlog" in names

    def test_detects_conan_deps(self, sbom_workspace):
        from core.commands.sbom import _detect_dependencies
        deps = _detect_dependencies()
        conan_deps = [d for d in deps if d["source"] == "conan"]
        assert len(conan_deps) == 2
        names = {d["name"] for d in conan_deps}
        assert "gtest" in names
        assert "nlohmann_json" in names

    def test_detects_pip_deps(self, sbom_workspace):
        from core.commands.sbom import _detect_dependencies
        deps = _detect_dependencies()
        pip_deps = [d for d in deps if d["source"] == "pip"]
        assert len(pip_deps) == 2
        names = {d["name"] for d in pip_deps}
        assert "pytest" in names
        assert "black" in names

    def test_empty_workspace_returns_empty(self, empty_workspace):
        from core.commands.sbom import _detect_dependencies
        deps = _detect_dependencies()
        assert deps == []

    def test_vcpkg_version_extraction(self, sbom_workspace):
        from core.commands.sbom import _detect_dependencies
        deps = _detect_dependencies()
        spdlog = [d for d in deps if d["name"] == "spdlog"][0]
        assert spdlog["version"] == "1.12.0"

    def test_conan_version_extraction(self, sbom_workspace):
        from core.commands.sbom import _detect_dependencies
        deps = _detect_dependencies()
        gtest = [d for d in deps if d["name"] == "gtest"][0]
        assert gtest["version"] == "1.14.0"


class TestSpdxGeneration:
    def test_spdx_structure(self, sbom_workspace):
        from core.commands.sbom import _gen_spdx, _detect_dependencies
        deps = _detect_dependencies()
        doc = _gen_spdx("TestProj", "1.0.0", deps)
        assert doc["spdxVersion"] == "SPDX-2.3"
        assert doc["dataLicense"] == "CC0-1.0"
        assert "packages" in doc
        assert "relationships" in doc

    def test_spdx_main_package(self, sbom_workspace):
        from core.commands.sbom import _gen_spdx
        doc = _gen_spdx("MyProj", "2.0.0", [])
        main_pkg = doc["packages"][0]
        assert main_pkg["name"] == "MyProj"
        assert main_pkg["versionInfo"] == "2.0.0"
        assert main_pkg["SPDXID"] == "SPDXRef-Package"

    def test_spdx_dep_packages(self, sbom_workspace):
        from core.commands.sbom import _gen_spdx
        deps = [{"name": "foo", "source": "vcpkg", "version": "1.0"}]
        doc = _gen_spdx("P", "1.0", deps)
        assert len(doc["packages"]) == 2  # main + 1 dep
        assert doc["packages"][1]["name"] == "foo"

    def test_spdx_relationships(self, sbom_workspace):
        from core.commands.sbom import _gen_spdx
        deps = [{"name": "foo", "source": "vcpkg", "version": "1.0"}]
        doc = _gen_spdx("P", "1.0", deps)
        assert len(doc["relationships"]) == 1
        rel = doc["relationships"][0]
        assert rel["relationshipType"] == "DEPENDS_ON"


class TestCycloneDxGeneration:
    def test_cyclonedx_structure(self, sbom_workspace):
        from core.commands.sbom import _gen_cyclonedx, _detect_dependencies
        deps = _detect_dependencies()
        doc = _gen_cyclonedx("TestProj", "1.0.0", deps)
        assert doc["bomFormat"] == "CycloneDX"
        assert doc["specVersion"] == "1.5"
        assert "components" in doc
        assert "metadata" in doc

    def test_cyclonedx_metadata(self, sbom_workspace):
        from core.commands.sbom import _gen_cyclonedx
        doc = _gen_cyclonedx("MyProj", "2.0.0", [])
        assert doc["metadata"]["component"]["name"] == "MyProj"
        assert doc["metadata"]["component"]["version"] == "2.0.0"

    def test_cyclonedx_components(self, sbom_workspace):
        from core.commands.sbom import _gen_cyclonedx
        deps = [{"name": "bar", "source": "conan", "version": "3.0"}]
        doc = _gen_cyclonedx("P", "1.0", deps)
        assert len(doc["components"]) == 1
        comp = doc["components"][0]
        assert comp["name"] == "bar"
        assert comp["purl"] == "pkg:conan/bar@3.0"


class TestSbomMain:
    def _extract_json(self, text: str) -> dict:
        """Extract JSON object from mixed stdout (Logger lines + JSON)."""
        # Find the first '{' and parse from there
        start = text.index("{")
        return json.loads(text[start:])

    def test_spdx_stdout(self, sbom_workspace, capsys):
        from core.commands.sbom import main
        main([])
        output = capsys.readouterr().out
        doc = self._extract_json(output)
        assert doc["spdxVersion"] == "SPDX-2.3"

    def test_cyclonedx_stdout(self, sbom_workspace, capsys):
        from core.commands.sbom import main
        main(["--format", "cyclonedx"])
        output = capsys.readouterr().out
        doc = self._extract_json(output)
        assert doc["bomFormat"] == "CycloneDX"

    def test_output_to_file(self, sbom_workspace):
        out_file = sbom_workspace / "sbom.json"
        from core.commands.sbom import main
        main(["--output", str(out_file)])
        assert out_file.exists()
        doc = json.loads(out_file.read_text(encoding="utf-8"))
        assert doc["spdxVersion"] == "SPDX-2.3"

    def test_empty_workspace_spdx(self, empty_workspace, capsys):
        from core.commands.sbom import main
        main([])
        output = capsys.readouterr().out
        doc = self._extract_json(output)
        assert len(doc["packages"]) == 1  # only main package
        assert len(doc["relationships"]) == 0
