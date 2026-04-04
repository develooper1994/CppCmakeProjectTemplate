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
    baseline = vcpkg.get("builtin_baseline", "")
    test_deps = vcpkg.get("test_dependencies", [])

    manifest: dict[str, Any] = {
        "name": ctx.name.lower().replace("_", "-"),
        "version-string": ctx.version,
    }

    if baseline:
        manifest["builtin-baseline"] = baseline

    # Dependencies (test dependencies like gtest)
    deps_list: list[Any] = []
    for dep in test_deps:
        if dep == "gtest":
            deps_list.append({"name": "gtest", "version>=": "1.14.0"})
        else:
            deps_list.append(dep)
    manifest["dependencies"] = deps_list

    if features:
        manifest["features"] = {}
        for feat in features:
            if feat == "mimalloc":
                manifest["features"][feat] = {
                    "description": "Use mimalloc as the global allocator backend",
                    "dependencies": ["mimalloc"],
                }
            elif feat == "jemalloc":
                manifest["features"][feat] = {
                    "description": "Use jemalloc as the global allocator backend",
                    "dependencies": ["jemalloc"],
                }
            else:
                manifest["features"][feat] = {
                    "description": f"Enable {feat} support",
                    "dependencies": [feat],
                }

    return json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"


def _gen_conanfile(ctx: ProjectContext) -> str:
    """Generate conanfile.py from tool.toml [deps.conan]."""
    conan = ctx.deps.get("conan", {})
    requires = conan.get("requires", [])
    test_reqs = conan.get("test_requires", [])
    alloc_versions = conan.get("allocator_versions", {})
    name = ctx.name

    # Determine class name
    class_name = name.replace("-", "").replace("_", "") + "Recipe"

    lines: list[str] = []
    lines.append("from conan import ConanFile")
    lines.append("from conan.tools.cmake import cmake_layout")
    lines.append("")
    lines.append("")
    lines.append(f"class {class_name}(ConanFile):")
    lines.append('    settings = "os", "compiler", "build_type", "arch"')
    lines.append('    generators = "CMakeDeps", "CMakeToolchain"')

    # Allocator options (if Allocators module is enabled)
    enabled_modules = set(ctx.cmake_modules.get("enabled", []))
    has_allocators = "Allocators" in enabled_modules

    if has_allocators:
        lines.append("")
        lines.append("    options = {")
        lines.append('        "allocator": ["default", "mimalloc", "jemalloc", "tcmalloc"],')
        lines.append("    }")
        lines.append("    default_options = {")
        lines.append('        "allocator": "default",')
        lines.append("    }")

    # Static requires (if any)
    if requires:
        req_items = ", ".join(f'"{r}"' for r in requires)
        lines.append(f"    requires = ({req_items},)")

    # Dynamic requirements method (allocator-based)
    if has_allocators:
        mim_ver = alloc_versions.get("mimalloc", "2.1.7")
        je_ver = alloc_versions.get("jemalloc", "5.3.0")
        tc_ver = alloc_versions.get("tcmalloc", "2.15")
        lines.append("")
        lines.append("    def requirements(self):")
        lines.append("        alloc = str(self.options.allocator)")
        lines.append('        if alloc == "mimalloc":')
        lines.append(f'            self.requires("mimalloc/{mim_ver}")')
        lines.append('        elif alloc == "jemalloc":')
        lines.append(f'            self.requires("jemalloc/{je_ver}")')
        lines.append('        elif alloc == "tcmalloc":')
        lines.append(f'            self.requires("gperftools/{tc_ver}")')

    # Build requirements (test dependencies)
    if test_reqs:
        lines.append("")
        lines.append("    def build_requirements(self):")
        lines.append("        # test_requires: gtest is only required for test builds and")
        lines.append("        # will not be propagated to downstream consumers.")
        for tr in test_reqs:
            lines.append(f'        self.test_requires("{tr}")')

    lines.append("")
    lines.append("    def layout(self):")
    lines.append("        cmake_layout(self)")
    lines.append("")

    return "\n".join(lines)


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
