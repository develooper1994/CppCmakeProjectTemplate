"""
core/generator/engine.py — Generation orchestrator.

Reads tool.toml, builds a context dict, dispatches to component generators,
and writes files through the manifest/merge system.
"""
from __future__ import annotations

import subprocess
import sys
import time
import traceback
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
    profile: str = "full"

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


def _read_git_config(key: str) -> str:
    """Read a git config value, returning an empty string when unavailable."""
    try:
        proc = subprocess.run(
            ["git", "config", key],
            cwd=Path.cwd(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return ""
    return proc.stdout.strip() if proc.returncode == 0 else ""


def resolve_project_metadata(project: dict[str, Any]) -> tuple[str, str]:
    """Resolve author/contact from config first, then git config, else warn."""
    author = str(project.get("author", "") or "").strip()
    contact = str(project.get("contact", "") or "").strip()

    if not author:
        author = _read_git_config("user.name")
        if author:
            Logger.info(f"Using git user.name as project author: {author}")
        else:
            Logger.warn("Project author is not set; pass --author or set git config user.name.")

    if not contact:
        contact = _read_git_config("user.email")
        if contact:
            Logger.info(f"Using git user.email as project contact: {contact}")
        else:
            Logger.warn("Project contact is not set; pass --contact or set git config user.email.")

    return author, contact


def resolve_profile_name(cfg: dict[str, Any]) -> str:
    """Resolve the active generation profile."""
    profile = (
        cfg.get("generate", {}).get("profile")
        or cfg.get("project", {}).get("profile")
        or "full"
    )
    return str(profile).strip().lower() or "full"


PROFILE_DEFAULT_FEATURES: dict[str, set[str]] = {
    "full": set(),
    "minimal": {"ci", "docker", "vscode", "extension", "docs"},
    "library": {"apps", "ci", "docker", "vscode", "extension"},
    "app": {"extension"},
    "embedded": {"extension", "docker", "docs"},
}


def _normalize_feature_list(values: Any) -> set[str]:
    if values is None:
        return set()
    if isinstance(values, str):
        items = values.split(",")
    elif isinstance(values, (list, tuple, set)):
        items = values
    else:
        return set()
    return {str(item).strip().lower() for item in items if str(item).strip()}


def get_enabled_features(ctx: ProjectContext) -> set[str]:
    return _normalize_feature_list(ctx.generate.get("with", []))


def get_disabled_features(ctx: ProjectContext) -> set[str]:
    profile_defaults = PROFILE_DEFAULT_FEATURES.get(ctx.profile, set())
    explicit = _normalize_feature_list(ctx.generate.get("without", []))
    return set(profile_defaults) | explicit


def is_feature_enabled(ctx: ProjectContext, feature: str, *, default: bool = True) -> bool:
    feature_name = str(feature).strip().lower()
    if feature_name in get_enabled_features(ctx):
        return True
    if feature_name in get_disabled_features(ctx):
        return False
    return default


def apply_profile_defaults(ctx: ProjectContext) -> None:
    """Apply profile-driven defaults directly onto the resolved context."""
    if not is_feature_enabled(ctx, "apps"):
        ctx.apps = []
    if not is_feature_enabled(ctx, "vscode", default=ctx.vscode.get("generate", True)):
        ctx.vscode = {**ctx.vscode, "generate": False}
    if not is_feature_enabled(ctx, "extension", default=ctx.extension.get("generate", True)):
        ctx.extension = {**ctx.extension, "generate": False}
    if not is_feature_enabled(ctx, "docs", default=ctx.docs.get("generate", True)):
        ctx.docs = {**ctx.docs, "generate": False}
    if not is_feature_enabled(ctx, "fuzz", default=ctx.tests.get("fuzz", False)):
        ctx.tests = {**ctx.tests, "fuzz": False}


def build_context(config: dict[str, Any] | None = None) -> ProjectContext:
    """Build a ProjectContext from tool.toml (or a provided dict)."""
    cfg = config if config is not None else load_tool_config()
    project = cfg.get("project", {})
    author, contact = resolve_project_metadata(project)
    profile = resolve_profile_name(cfg)

    ctx = ProjectContext(
        name=project.get("name", "CppCmakeProjectTemplate"),
        version=project.get("version", "1.0.0"),
        description=project.get("description", ""),
        author=author,
        contact=contact,
        license=project.get("license", "MIT"),
        cxx_standard=project.get("cxx_standard", "17"),
        cmake_minimum=project.get("cmake_minimum", "3.25"),
        profile=profile,
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
    apply_profile_defaults(ctx)
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
    "cmake-root": ("core.generator.cmake_root", "generate_all"),
    "cmake-targets": ("core.generator.cmake_targets", "generate_all"),
    "sources": ("core.generator.sources", "generate_all"),
    "ci": ("core.generator.ci", "generate_all"),
    "deps": ("core.generator.deps", "generate_all"),
    "configs": ("core.generator.configs", "generate_all"),
    "presets": ("core.generator.presets", "generate_all"),
}

PROFILE_COMPONENTS: dict[str, tuple[str, ...]] = {
    "full": tuple(COMPONENT_REGISTRY.keys()),
    "minimal": (
        "cmake-dynamic",
        "cmake-static",
        "cmake-root",
        "cmake-targets",
        "sources",
        "deps",
        "configs",
        "presets",
    ),
    "library": (
        "cmake-dynamic",
        "cmake-static",
        "cmake-root",
        "cmake-targets",
        "sources",
        "deps",
        "configs",
        "presets",
    ),
    "app": tuple(COMPONENT_REGISTRY.keys()),
    "embedded": tuple(COMPONENT_REGISTRY.keys()),
}


def get_profile_components(profile: str) -> list[str]:
    """Return the component list for a named generation profile."""
    normalized = str(profile or "full").strip().lower() or "full"
    return list(PROFILE_COMPONENTS.get(normalized, PROFILE_COMPONENTS["full"]))


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
    timings: dict[str, float] = field(default_factory=dict)

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
    debug: bool = False,
    verbose: bool = False,
) -> GenerateResult:
    """Run the generation engine.

    Args:
        target_dir: Root directory where files are written.
        components: List of component names to generate. None = all registered.
        policy: Conflict resolution policy. None = read from tool.toml.
        dry_run: If True, no files are written.
        config: Optional config dict (overrides reading tool.toml).
        debug: If True, print full tracebacks and per-component timing.
        verbose: If True, print extra progress messages.

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
    to_run = components if components else get_profile_components(ctx.profile)
    if not is_feature_enabled(ctx, "ci"):
        to_run = [name for name in to_run if name != "ci"]

    result = GenerateResult()

    for comp_name in to_run:
        if comp_name not in COMPONENT_REGISTRY:
            Logger.warn(f"Unknown component: {comp_name}")
            result.errors.append(f"unknown:{comp_name}")
            continue

        if verbose:
            Logger.info(f"  → generating component: {comp_name}")

        t0 = time.monotonic()
        try:
            gen_func = _load_generator(comp_name)
            files = gen_func(ctx, target_dir)
        except Exception as exc:
            Logger.error(f"Generator {comp_name} failed: {exc}")
            if debug:
                traceback.print_exc()
            result.errors.append(f"{comp_name}:{exc}")
            continue
        elapsed = time.monotonic() - t0

        if debug or verbose:
            result.timings[comp_name] = round(elapsed, 4)
            if debug:
                Logger.info(f"  ⏱ {comp_name}: {elapsed:.4f}s ({len(files)} files)")

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
                if debug:
                    traceback.print_exc()
                result.errors.append(f"{rel_path}:{exc}")

    if not dry_run:
        manifest.save()

    if debug and result.timings:
        total = sum(result.timings.values())
        Logger.info(f"  ⏱ Total generation time: {total:.4f}s")

    return result
