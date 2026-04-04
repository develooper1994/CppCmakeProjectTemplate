"""
core/generator/ci.py — CI/CD workflow static tracking.

Reads existing .github/ files from the project directory and tracks them
in the generation manifest. Workflows are complex hand-maintained YAML,
so we use the static-tracking approach (read + hash, no template generation).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

if __name__ != "__main__":
    from core.generator.engine import ProjectContext, is_feature_enabled
    from core.utils.common import Logger


# Workflow files tracked by the generator
CI_WORKFLOWS = [
    "ci.yml",
    "clang_tidy_fix.yml",
    "cmake_format.yml",
    "fuzz-afl.yml",
    "fuzz.yml",
    "gitleaks.yml",
    "musl_nightly.yml",
    "perf_regression.yml",
    "release.yml",
    "reusable-ci.yml",
    "security_scan.yml",
    "vsix-package.yml",
]

ISSUE_TEMPLATES = [
    "bug_report.md",
]


def _find_project_root() -> Path:
    """Walk up from this file to find the directory containing tool.toml."""
    p = Path(__file__).resolve()
    for parent in [p] + list(p.parents):
        if (parent / "tool.toml").exists():
            return parent
    raise FileNotFoundError("Cannot find project root (no tool.toml found)")


def generate_all(ctx: ProjectContext, target_dir: Path) -> dict[str, str]:
    if not is_feature_enabled(ctx, "ci"):
        return {}

    root = _find_project_root()
    files: dict[str, str] = {}

    # Workflows
    wf_dir = root / ".github" / "workflows"
    if wf_dir.is_dir():
        for wf in sorted(wf_dir.iterdir()):
            if wf.suffix in (".yml", ".yaml") and wf.is_file():
                rel = f".github/workflows/{wf.name}"
                files[rel] = wf.read_text(encoding="utf-8")
    else:
        Logger.warn("ci: .github/workflows/ not found — no workflows to track")

    # Issue templates
    tmpl_dir = root / ".github" / "ISSUE_TEMPLATE"
    if tmpl_dir.is_dir():
        for tmpl in sorted(tmpl_dir.iterdir()):
            if tmpl.is_file():
                rel = f".github/ISSUE_TEMPLATE/{tmpl.name}"
                files[rel] = tmpl.read_text(encoding="utf-8")

    return files
