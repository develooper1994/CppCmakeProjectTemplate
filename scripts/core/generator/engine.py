"""
core/generator/engine.py — Generation orchestrator.

Reads tool.toml, builds a context dict, dispatches to component generators,
and writes files through the manifest/merge system.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.utils.common import Logger, GlobalConfig
from core.utils.config_loader import load_tool_config
from core.generator.manifest import GenerationManifest
from core.generator.merge import ConflictPolicy, MergeResult, resolve_write


# ---------------------------------------------------------------------------
# Context — the fully-resolved project description
# ---------------------------------------------------------------------------

@dataclass
class ProjectContext:
    """Fully-resolved project description derived from tool.toml."""

    # [project]
    name: str = "CppCmakeProjectTemplate"
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    contact: str = ""
    license: str = "MIT"
    cxx_standard: str = "17"
    cmake_minimum: str = "3.25"

    # [[project.libs]]
    libs: list[dict[str, Any]] = field(default_factory=list)

    # [[project.apps]]
    apps: list[dict[str, Any]] = field(default_factory=list)

    # [project.tests]
    tests: dict[str, Any] = field(default_factory=lambda: {
        "framework": "gtest", "fuzz": True, "auto_generate": True,
    })

    # [ci]
    ci: dict[str, Any] = field(default_factory=dict)

    # [deps]
    deps: dict[str, Any] = field(default_factory=dict)

    # [docker]
    docker: dict[str, Any] = field(default_factory=dict)

    # [cmake_modules]
    cmake_modules: dict[str, Any] = field(default_factory=dict)

    # [vscode]
    vscode: dict[str, Any] = field(default_factory=dict)

    # [git]
    git: dict[str, Any] = field(default_factory=dict)

    # [docs]
    docs: dict[str, Any] = field(default_factory=dict)

    # [extension]
    extension: dict[str, Any] = field(default_factory=dict)

    # [generate]
    generate: dict[str, Any] = field(default_factory=dict)

    # [build]
    build: dict[str, Any] = field(default_factory=dict)

    # [presets]
    presets: dict[str, Any] = field(default_factory=dict)

    # [security]
    security: dict[str, Any] = field(default_factory=dict)

    # [hooks]
    hooks: dict[str, Any] = field(default_factory=dict)

    # [embedded]
    embedded: dict[str, Any] = field(default_factory=dict)

    # [gpu]
    gpu: dict[str, Any] = field(default_factory=dict)

    # Raw config for passthrough
    raw: dict[str, Any] = field(default_factory=dict)


def build_context(config: dict[str, Any] | None = None) -> ProjectContext:
    """Build a ProjectContext from tool.toml (or a provided dict)."""
    cfg = config if config is not None else load_tool_config()
    project = cfg.get("project", {})

    ctx = ProjectContext(
        name=project.get("name", "CppCmakeProjectTemplate"),
        version=project.get("version", "1.0.0"),
        description=project.get("description", ""),
        author=project.get("author", ""),
        contact=project.get("contact", ""),
        license=project.get("license", "MIT"),
        cxx_standard=project.get("cxx_standard", "17"),
        cmake_minimum=project.get("cmake_minimum", "3.25"),
        libs=cfg.get("project", {}).get("libs", []),
        apps=cfg.get("project", {}).get("apps", []),
        tests=project.get("tests", {"framework": "gtest", "fuzz": True, "auto_generate": True}),
        ci=cfg.get("ci", {}),
        deps=cfg.get("deps", {}),
        docker=cfg.get("docker", {}),
        cmake_modules=cfg.get("cmake_modules", {}),
        vscode=cfg.get("vscode", {}),
        git=cfg.get("git", {}),
        docs=cfg.get("docs", {}),
        extension=cfg.get("extension", {}),
        generate=cfg.get("generate", {}),
        build=cfg.get("build", {}),
        presets=cfg.get("presets", {}),
        security=cfg.get("security", {}),
        hooks=cfg.get("hooks", {}),
        embedded=cfg.get("embedded", {}),
        gpu=cfg.get("gpu", {}),
        raw=cfg,
    )
    return ctx


# ---------------------------------------------------------------------------
# Component registry
# ---------------------------------------------------------------------------

# Maps component name → (module_path, function_name)
# Each generator function has signature: (ctx, target_dir) -> dict[str, str]
# Returns {relative_path: content} for all files it wants to write.
COMPONENT_REGISTRY: dict[str, tuple[str, str]] = {
    "cmake-dynamic": ("core.generator.cmake_dynamic", "generate_all"),
    "cmake-static": ("core.generator.cmake_static", "generate_all"),
}


def _load_generator(component: str):
    """Lazily import and return the generator function for a component."""
    if component not in COMPONENT_REGISTRY:
        raise ValueError(f"Unknown generator component: {component}")
    mod_path, func_name = COMPONENT_REGISTRY[component]
    import importlib
    mod = importlib.import_module(mod_path)
    return getattr(mod, func_name)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

@dataclass
class GenerateResult:
    """Summary of a generation run."""
    created: list[str] = field(default_factory=list)
    written: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.created) + len(self.written) + len(self.skipped) + len(self.conflicts)

    def summary(self) -> str:
        parts = []
        if self.created:
            parts.append(f"{len(self.created)} created")
        if self.written:
            parts.append(f"{len(self.written)} updated")
        if self.skipped:
            parts.append(f"{len(self.skipped)} skipped")
        if self.conflicts:
            parts.append(f"{len(self.conflicts)} conflicts")
        if self.errors:
            parts.append(f"{len(self.errors)} errors")
        return ", ".join(parts) if parts else "nothing to do"


def generate(
    target_dir: Path,
    components: list[str] | None = None,
    policy: ConflictPolicy | None = None,
    dry_run: bool = False,
    config: dict[str, Any] | None = None,
) -> GenerateResult:
    """Run the generation engine.

    Args:
        target_dir: Root directory where files are written.
        components: List of component names to generate. None = all registered.
        policy: Conflict resolution policy. None = read from tool.toml.
        dry_run: If True, no files are written.
        config: Optional config dict (overrides reading tool.toml).

    Returns:
        GenerateResult with summary of actions taken.
    """
    ctx = build_context(config)

    # Resolve conflict policy
    if policy is None:
        policy_str = ctx.generate.get("on_conflict", "ask")
        try:
            policy = ConflictPolicy(policy_str)
        except ValueError:
            policy = ConflictPolicy.ASK

    # Manifest
    manifest_rel = ctx.generate.get("manifest_file", ".tool/generation_manifest.json")
    manifest_path = target_dir / manifest_rel
    manifest = GenerationManifest(manifest_path)

    # Backup dir
    backup_rel = ctx.generate.get("backup_dir", ".tool/backup")
    backup_dir = target_dir / backup_rel

    # Determine which components to run
    to_run = components if components else list(COMPONENT_REGISTRY.keys())

    result = GenerateResult()

    for comp_name in to_run:
        if comp_name not in COMPONENT_REGISTRY:
            Logger.warning(f"Unknown component: {comp_name}")
            result.errors.append(f"unknown:{comp_name}")
            continue

        try:
            gen_func = _load_generator(comp_name)
            files = gen_func(ctx, target_dir)
        except Exception as exc:
            Logger.error(f"Generator {comp_name} failed: {exc}")
            result.errors.append(f"{comp_name}:{exc}")
            continue

        for rel_path, content in files.items():
            target_file = target_dir / rel_path
            try:
                action = resolve_write(
                    target=target_file,
                    new_content=content,
                    rel_path=rel_path,
                    manifest=manifest,
                    policy=policy,
                    backup_dir=backup_dir,
                    dry_run=dry_run,
                )

                if action == MergeResult.CREATED:
                    result.created.append(rel_path)
                    if not dry_run:
                        manifest.record(rel_path, content, comp_name)
                elif action == MergeResult.WRITTEN:
                    result.written.append(rel_path)
                    if not dry_run:
                        manifest.record(rel_path, content, comp_name)
                elif action == MergeResult.SKIPPED:
                    result.skipped.append(rel_path)
                elif action == MergeResult.CONFLICT:
                    result.conflicts.append(rel_path)

            except Exception as exc:
                Logger.error(f"Failed to write {rel_path}: {exc}")
                result.errors.append(f"{rel_path}:{exc}")

    if not dry_run:
        manifest.save()

    return result
