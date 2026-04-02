"""
core/generator — Full project generation engine.

Public API:
    generate_project(target_dir, **kwargs) — generate all components
    generate_component(target_dir, component, **kwargs) — generate one component
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from core.generator.engine import (
    GenerateResult,
    ProjectContext,
    build_context,
    generate,
)
from core.generator.merge import ConflictPolicy


def generate_project(
    target_dir: Path | str,
    *,
    policy: str | ConflictPolicy | None = None,
    dry_run: bool = False,
    config: dict[str, Any] | None = None,
) -> GenerateResult:
    """Generate all project files into *target_dir*."""
    target = Path(target_dir)
    target.mkdir(parents=True, exist_ok=True)
    pol = _resolve_policy(policy)
    return generate(target, components=None, policy=pol, dry_run=dry_run, config=config)


def generate_component(
    target_dir: Path | str,
    component: str,
    *,
    policy: str | ConflictPolicy | None = None,
    dry_run: bool = False,
    config: dict[str, Any] | None = None,
) -> GenerateResult:
    """Generate a single component into *target_dir*."""
    target = Path(target_dir)
    target.mkdir(parents=True, exist_ok=True)
    pol = _resolve_policy(policy)
    return generate(target, components=[component], policy=pol, dry_run=dry_run, config=config)


def _resolve_policy(policy: str | ConflictPolicy | None) -> ConflictPolicy | None:
    if policy is None:
        return None
    if isinstance(policy, ConflictPolicy):
        return policy
    return ConflictPolicy(policy)
