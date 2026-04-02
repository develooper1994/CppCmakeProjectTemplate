"""
core/generator/merge.py — Conflict resolution for generated files.

When regenerating files that the user may have modified, this module
decides what to do: overwrite, skip, ask, or attempt a 3-way merge.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from enum import Enum
from pathlib import Path

from core.utils.common import Logger
from core.generator.manifest import GenerationManifest


class ConflictPolicy(Enum):
    ASK = "ask"
    OVERWRITE = "overwrite"
    SKIP = "skip"
    MERGE = "merge"


class MergeResult(Enum):
    WRITTEN = "written"
    SKIPPED = "skipped"
    MERGED = "merged"
    CONFLICT = "conflict"
    CREATED = "created"


def resolve_write(
    target: Path,
    new_content: str,
    rel_path: str,
    manifest: GenerationManifest,
    policy: ConflictPolicy,
    backup_dir: Path | None = None,
    dry_run: bool = False,
) -> MergeResult:
    """Decide how to write *new_content* to *target*, respecting user edits.

    Returns the action taken.
    """
    # Case 1: file doesn't exist → just create
    if not target.exists():
        if not dry_run:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(new_content, encoding="utf-8")
        return MergeResult.CREATED

    disk_content = target.read_text(encoding="utf-8")

    # Case 2: disk matches new content → nothing to do
    if disk_content == new_content:
        return MergeResult.SKIPPED

    # Case 3: file was never generated (no manifest entry) → treat as user file
    user_modified = manifest.file_was_modified_by_user(rel_path, disk_content)

    if not user_modified:
        # File matches last generation → safe to overwrite silently
        if not dry_run:
            target.write_text(new_content, encoding="utf-8")
        return MergeResult.WRITTEN

    # Case 4: user modified the file → apply conflict policy
    if policy == ConflictPolicy.OVERWRITE:
        if not dry_run:
            _backup(target, backup_dir)
            target.write_text(new_content, encoding="utf-8")
        return MergeResult.WRITTEN

    if policy == ConflictPolicy.SKIP:
        Logger.info(f"  skip (user-modified): {rel_path}")
        return MergeResult.SKIPPED

    if policy == ConflictPolicy.MERGE:
        return _try_merge(target, disk_content, new_content, rel_path, manifest, backup_dir, dry_run)

    if policy == ConflictPolicy.ASK:
        return _ask_user(target, disk_content, new_content, rel_path, manifest, backup_dir, dry_run)

    return MergeResult.SKIPPED


def _backup(target: Path, backup_dir: Path | None) -> None:
    if backup_dir is None:
        return
    dest = backup_dir / target.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(target, dest)


def _try_merge(
    target: Path,
    disk_content: str,
    new_content: str,
    rel_path: str,
    manifest: GenerationManifest,
    backup_dir: Path | None,
    dry_run: bool,
) -> MergeResult:
    """Attempt 3-way merge using git merge-file."""
    entry = manifest.get_entry(rel_path)
    if entry is None:
        # No base version available → can't merge
        Logger.warn(f"  conflict (no base): {rel_path}")
        return MergeResult.CONFLICT

    # We need the original generated content as the base.
    # Since we only store the hash, we can't reconstruct it.
    # Fall back to overwrite with backup.
    if not dry_run:
        _backup(target, backup_dir)
        target.write_text(new_content, encoding="utf-8")
    Logger.info(f"  overwrite (merge unavailable): {rel_path}")
    return MergeResult.WRITTEN


def _ask_user(
    target: Path,
    disk_content: str,
    new_content: str,
    rel_path: str,
    manifest: GenerationManifest,
    backup_dir: Path | None,
    dry_run: bool,
) -> MergeResult:
    """Prompt the user for conflict resolution."""
    Logger.warn(f"  CONFLICT: {rel_path} was modified by user.")
    print(f"\n  [o] Overwrite (backup old)  [s] Skip  [d] Show diff")
    try:
        choice = input("  Choice [o/s/d]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        choice = "s"

    if choice == "d":
        _show_diff(disk_content, new_content, rel_path)
        try:
            choice = input("  After diff — [o] Overwrite  [s] Skip: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            choice = "s"

    if choice == "o":
        if not dry_run:
            _backup(target, backup_dir)
            target.write_text(new_content, encoding="utf-8")
        return MergeResult.WRITTEN

    return MergeResult.SKIPPED


def _show_diff(old: str, new: str, label: str) -> None:
    """Print a unified diff between old and new content."""
    try:
        import difflib

        diff = difflib.unified_diff(
            old.splitlines(keepends=True),
            new.splitlines(keepends=True),
            fromfile=f"a/{label} (disk)",
            tofile=f"b/{label} (generated)",
        )
        print("".join(diff))
    except Exception as exc:
        Logger.warn(f"  diff failed for {label}: {exc}")
        print("  (diff unavailable)")
