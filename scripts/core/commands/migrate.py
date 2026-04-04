"""
core/commands/migrate.py — Migration wizard for template upgrades
=================================================================

Detects the current project version, compares against the latest
template version, and offers incremental upgrades with drift detection.

Usage:
  tool migrate                    # interactive upgrade
  tool migrate --check            # check for available upgrades
  tool migrate --dry-run          # preview changes without writing
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from core.utils.common import Logger, CLIResult, PROJECT_ROOT

COMMAND_META = {
    "name": "migrate",
    "description": "Migration wizard for template version upgrades",
}


def _read_manifest() -> dict | None:
    """Read the generation manifest to detect current state."""
    manifest_path = PROJECT_ROOT / ".tool" / "generation_manifest.json"
    if not manifest_path.exists():
        return None
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _read_version() -> str:
    """Read current project VERSION."""
    version_file = PROJECT_ROOT / "VERSION"
    if version_file.exists():
        return version_file.read_text(encoding="utf-8").strip()
    return "unknown"


def _detect_drift(manifest: dict) -> list[dict[str, str]]:
    """Detect files that have drifted from their generated state.

    Compares actual file content hashes against manifest records.
    """
    import hashlib

    drifted = []
    for rel_path, info in manifest.get("files", {}).items():
        full_path = PROJECT_ROOT / rel_path
        if not full_path.exists():
            drifted.append({
                "file": rel_path,
                "status": "deleted",
                "detail": "File was generated but has been deleted",
            })
            continue

        expected_hash = info.get("hash", "")
        if not expected_hash:
            continue

        actual_hash = hashlib.sha256(
            full_path.read_bytes()
        ).hexdigest()

        if actual_hash != expected_hash:
            drifted.append({
                "file": rel_path,
                "status": "modified",
                "detail": "File has been manually modified since last generation",
            })

    return drifted


def _check_upgradeable() -> dict[str, str | list]:
    """Check what can be upgraded."""
    manifest = _read_manifest()
    version = _read_version()

    result = {
        "current_version": version,
        "has_manifest": manifest is not None,
        "drift": [],
        "recommendations": [],
    }

    if manifest is None:
        result["recommendations"].append(
            "No generation manifest found. Run 'tool generate' first to establish baseline."
        )
        return result

    drift = _detect_drift(manifest)
    result["drift"] = drift

    if drift:
        modified = [d for d in drift if d["status"] == "modified"]
        deleted = [d for d in drift if d["status"] == "deleted"]
        if modified:
            result["recommendations"].append(
                f"{len(modified)} file(s) have been manually modified. "
                "These will be preserved during migration (backup created)."
            )
        if deleted:
            result["recommendations"].append(
                f"{len(deleted)} generated file(s) have been deleted. "
                "They will be regenerated during migration."
            )
    else:
        result["recommendations"].append(
            "No drift detected. Safe to regenerate all files."
        )

    return result


def main(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(
        prog="tool migrate",
        description="Migration wizard for template upgrades",
    )
    parser.add_argument("--check", action="store_true",
                        help="Check migration status without making changes")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview migration without writing files")
    parser.add_argument("--force", action="store_true",
                        help="Force regeneration of all files (overwrite drift)")

    args = parser.parse_args(argv)

    Logger.info("🔍 Analyzing project state...")
    status = _check_upgradeable()

    Logger.info(f"  Project version: {status['current_version']}")
    Logger.info(f"  Manifest: {'found' if status['has_manifest'] else 'not found'}")

    if status["drift"]:
        Logger.warn(f"  Drift detected: {len(status['drift'])} file(s)")
        for d in status["drift"][:10]:
            icon = "📝" if d["status"] == "modified" else "🗑️"
            Logger.info(f"    {icon} {d['file']} ({d['status']})")
        if len(status["drift"]) > 10:
            Logger.info(f"    ... and {len(status['drift']) - 10} more")
    else:
        Logger.success("  No drift detected.")

    for rec in status["recommendations"]:
        Logger.info(f"  💡 {rec}")

    if args.check:
        return

    if not status["has_manifest"] and not args.force:
        Logger.error(
            "No manifest found. Run 'tool generate' first, or use --force to regenerate everything."
        )
        sys.exit(1)

    # Perform migration = regenerate with conflict policy
    from core.generator.engine import generate, GenerateResult
    from core.generator.merge import ConflictPolicy

    policy = ConflictPolicy.OVERWRITE if args.force else ConflictPolicy.BACKUP

    Logger.info(f"\n{'[DRY-RUN] ' if args.dry_run else ''}Running migration...")
    result = generate(
        target_dir=PROJECT_ROOT,
        policy=policy,
        dry_run=args.dry_run,
        incremental=not args.force,
    )

    if result.errors:
        Logger.error(f"Migration completed with {len(result.errors)} error(s):")
        for err in result.errors:
            Logger.error(f"  {err}")
    else:
        Logger.success(f"Migration complete: {result.summary()}")
