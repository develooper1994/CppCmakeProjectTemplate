"""
core/generator/configs.py — Static config file tracking.

Tracks existing project configuration files that are rarely changed:
  - Docker files: docker/Dockerfile*
  - VS Code: .vscode/*.json
  - Git configs: .gitignore, .editorconfig, .clang-format, etc.
  - Extension: extension/package.json, etc.
  - Root configs: pyproject.toml, .clangd, .cmake-format, etc.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

if __name__ != "__main__":
    from core.generator.engine import ProjectContext

# Root-level config files to track
ROOT_CONFIGS = [
    ".clang-format",
    ".clang-tidy",
    ".clangd",
    ".cmake-format",
    ".cppcheck-suppressions.txt",
    ".dockerignore",
    ".editorconfig",
    ".gitignore",
    "pyproject.toml",
    "LICENSE",
    "VERSION",
]


def _find_project_root() -> Path:
    p = Path(__file__).resolve()
    for parent in [p] + list(p.parents):
        if (parent / "tool.toml").exists():
            return parent
    raise FileNotFoundError("Cannot find project root")


def generate_all(ctx: ProjectContext, target_dir: Path) -> dict[str, str]:
    root = _find_project_root()
    files: dict[str, str] = {}

    # Root config files
    for fname in ROOT_CONFIGS:
        fpath = root / fname
        if fpath.is_file():
            try:
                files[fname] = fpath.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                pass  # skip binary files

    # Docker files
    docker_dir = root / "docker"
    if docker_dir.is_dir():
        for df in sorted(docker_dir.iterdir()):
            if df.is_file() and df.name.startswith("Dockerfile"):
                files[f"docker/{df.name}"] = df.read_text(encoding="utf-8")

    # VS Code configs
    vscode_dir = root / ".vscode"
    if vscode_dir.is_dir():
        for vf in sorted(vscode_dir.iterdir()):
            if vf.is_file() and vf.suffix == ".json":
                files[f".vscode/{vf.name}"] = vf.read_text(encoding="utf-8")

    # Extension key files
    ext_dir = root / "extension"
    if ext_dir.is_dir():
        for ef_name in ("package.json",):
            ef = ext_dir / ef_name
            if ef.is_file():
                files[f"extension/{ef_name}"] = ef.read_text(encoding="utf-8")

    return files
