#!/usr/bin/env python3
"""
scripts/plugins/hooks/pre_commit_preview.py

Preview which `.pre-commit-config.yaml` hooks would run for the staged files.
This script DOES NOT execute hooks — it only prints a human-readable preview of
which hooks match which staged files and suggested commands to run them.

Usage:
  python3 scripts/plugins/hooks/pre_commit_preview.py

This file is intended to be added to `scripts/plugins/hooks/` as a template and
reviewed by maintainers. It intentionally does not execute anything by default.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


def find_project_root(start: Path) -> Path:
    p = start.resolve()
    for _ in range(20):
        if (p / ".pre-commit-config.yaml").exists() or (p / ".git").exists():
            return p
        if p.parent == p:
            break
        p = p.parent
    return start.resolve()


def load_precommit_config(root: Path) -> dict:
    cfg_path = root / ".pre-commit-config.yaml"
    if not cfg_path.exists():
        print("No .pre-commit-config.yaml found in project root.")
        return {}
    try:
        import yaml
    except Exception:
        print("Please install PyYAML (pip install pyyaml) to parse .pre-commit-config.yaml")
        return {}
    with cfg_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_staged_files() -> list[str]:
    try:
        p = subprocess.run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"], capture_output=True, text=True)
    except FileNotFoundError:
        return []
    if p.returncode != 0:
        return []
    return [ln.strip() for ln in p.stdout.splitlines() if ln.strip()]


def match_pattern(pattern: str, filename: str) -> bool:
    try:
        return re.search(pattern, filename) is not None
    except re.error:
        return False


def main() -> int:
    start = Path(__file__).parent
    root = find_project_root(start)
    cfg = load_precommit_config(root)
    if not cfg:
        return 0

    staged = get_staged_files()
    print(f"Staged files ({len(staged)}):")
    for s in staged:
        print("  -", s)
    print()

    repos = cfg.get("repos", [])
    if not repos:
        print("No hooks configured in .pre-commit-config.yaml")
        return 0

    print("Preview of hooks matching staged files (no hooks will be executed):\n")
    for repo in repos:
        repo_name = repo.get("repo", "local")
        repo_rev = repo.get("rev", "")
        hooks = repo.get("hooks", [])
        for hook in hooks:
            hook_id = hook.get("id") or hook.get("name") or "<no-id>"
            files_pat = hook.get("files") or repo.get("files")
            entry = hook.get("entry")
            language = hook.get("language")

            matched = []
            if files_pat:
                for f in staged:
                    if match_pattern(files_pat, f):
                        matched.append(f)

            if matched:
                print(f"Hook: {hook_id}")
                print(f"  Repo: {repo_name} {repo_rev}")
                print(f"  Entry: {entry}")
                print(f"  Language: {language}")
                print(f"  Files pattern: {files_pat}")
                print(f"  Matched staged files ({len(matched)}):")
                for m in matched:
                    print(f"    - {m}")
                # Suggested command (informational only)
                if entry:
                    if language and language.startswith("python"):
                        print(f"  Suggested: {sys.executable} {entry} <files>")
                    else:
                        print(f"  Suggested: sh -c \"{entry} <files>\"")
                else:
                    print(f"  Suggested: pre-commit run {hook_id} --files <files>")
                print()

    print("End of preview. This script only prints a preview and does not execute hooks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
