"""
core/generator/deps.py — Dependency file generators.

Generates from [deps] in tool.toml:
  - vcpkg.json
  - conanfile.py

Tracks hook config files statically:
  - .pre-commit-config.yaml
  - .gitleaks.toml
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

if __name__ != "__main__":
    from core.generator.engine import ProjectContext


def _gen_vcpkg_json(ctx: ProjectContext) -> str:
    """Generate vcpkg.json from tool.toml [deps.vcpkg]."""
    vcpkg = ctx.deps.get("vcpkg", {})
    features = vcpkg.get("features", [])

    manifest: dict[str, Any] = {
        "name": ctx.name.lower().replace("_", "-"),
        "version-string": ctx.version,
        "dependencies": [],
    }

    if features:
        manifest["features"] = {}
        for feat in features:
            manifest["features"][feat] = {
                "description": f"Enable {feat} support",
                "dependencies": [feat],
            }

    return json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"


def _gen_conanfile(ctx: ProjectContext) -> str:
    """Generate conanfile.py from tool.toml [deps.conan]."""
    conan = ctx.deps.get("conan", {})
    requires = conan.get("requires", [])
    name = ctx.name
    version = ctx.version

    req_lines = ""
    if requires:
        req_items = ", ".join(f'"{r}"' for r in requires)
        req_lines = f"    requires = ({req_items},)"

    return f'''\
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class {name.replace("-", "").replace("_", "")}Recipe(ConanFile):
    name = "{name.lower()}"
    version = "{version}"
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
{req_lines}

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
'''


def _find_project_root() -> Path:
    p = Path(__file__).resolve()
    for parent in [p] + list(p.parents):
        if (parent / "tool.toml").exists():
            return parent
    raise FileNotFoundError("Cannot find project root")


def generate_all(ctx: ProjectContext, target_dir: Path) -> dict[str, str]:
    root = _find_project_root()
    files: dict[str, str] = {}

    # Generated files
    files["vcpkg.json"] = _gen_vcpkg_json(ctx)
    files["conanfile.py"] = _gen_conanfile(ctx)

    # Static tracking for hook configs
    for fname in (".pre-commit-config.yaml", ".gitleaks.toml"):
        fpath = root / fname
        if fpath.is_file():
            files[fname] = fpath.read_text(encoding="utf-8")

    return files
