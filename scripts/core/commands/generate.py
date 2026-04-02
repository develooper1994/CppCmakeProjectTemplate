"""
core/commands/generate.py — `tool generate` CLI command.

Generates project files from tool.toml configuration.

Usage:
    tool generate                              # regenerate all components
    tool generate --target-dir /path/to/dir    # generate into a new directory
    tool generate --component cmake-dynamic    # regenerate one component
    tool generate --dry-run                    # preview without writing
    tool generate --diff                       # show diff against existing
    tool generate --merge                      # use merge conflict resolution
    tool generate --force                      # overwrite without asking
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from core.utils.common import Logger, GlobalConfig, PROJECT_ROOT


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="tool generate",
        description="Generate project files from tool.toml",
    )
    parser.add_argument(
        "--target-dir", "-t",
        type=Path,
        default=None,
        help="Target directory (default: project root). Created if missing.",
    )
    parser.add_argument(
        "--component", "-c",
        type=str,
        default=None,
        help="Generate only a specific component (e.g. cmake-dynamic).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Preview changes without writing files.",
    )
    parser.add_argument(
        "--diff",
        action="store_true",
        default=False,
        help="Show diff between existing and generated files.",
    )
    parser.add_argument(
        "--merge",
        action="store_true",
        default=False,
        help="Use merge conflict resolution for user-modified files.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        default=False,
        help="Overwrite all files without asking (backup created).",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        default=False,
        dest="list_components",
        help="List available generator components.",
    )

    args = parser.parse_args(argv)

    # Use global dry-run if set
    dry_run = args.dry_run or GlobalConfig.DRY_RUN

    # Import generator lazily
    from core.generator.engine import COMPONENT_REGISTRY, generate, build_context
    from core.generator.merge import ConflictPolicy

    if args.list_components:
        Logger.info("Available generator components:")
        for name in sorted(COMPONENT_REGISTRY.keys()):
            mod_path, func = COMPONENT_REGISTRY[name]
            Logger.info(f"  {name:20s} → {mod_path}.{func}")
        return

    # Resolve target directory
    target_dir = args.target_dir or PROJECT_ROOT
    target_dir = Path(target_dir).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    # Resolve conflict policy
    policy = None
    if args.force:
        policy = ConflictPolicy.OVERWRITE
    elif args.merge:
        policy = ConflictPolicy.MERGE
    # else: read from tool.toml

    # Determine components
    components = [args.component] if args.component else None

    if args.diff:
        _show_diff(target_dir, components)
        return

    Logger.info(f"Generating into: {target_dir}")
    if dry_run:
        Logger.info("(dry-run mode — no files will be written)")

    result = generate(
        target_dir=target_dir,
        components=components,
        policy=policy,
        dry_run=dry_run,
    )

    # Report results
    if result.created:
        for f in result.created:
            Logger.success(f"  + {f}")
    if result.written:
        for f in result.written:
            Logger.info(f"  ~ {f}")
    if result.skipped:
        for f in result.skipped:
            Logger.debug(f"  . {f}")
    if result.conflicts:
        for f in result.conflicts:
            Logger.warning(f"  ! {f}")
    if result.errors:
        for f in result.errors:
            Logger.error(f"  ✗ {f}")

    Logger.info(f"Done: {result.summary()}")

    if result.errors:
        sys.exit(1)


def _show_diff(target_dir: Path, components: list[str] | None) -> None:
    """Show unified diff between existing files and what would be generated."""
    import difflib
    from core.generator.engine import generate, build_context, COMPONENT_REGISTRY

    ctx = build_context()
    to_run = components if components else list(COMPONENT_REGISTRY.keys())

    for comp_name in to_run:
        if comp_name not in COMPONENT_REGISTRY:
            continue
        from core.generator.engine import _load_generator
        gen_func = _load_generator(comp_name)
        files = gen_func(ctx, target_dir)

        for rel_path, new_content in files.items():
            target_file = target_dir / rel_path
            if target_file.exists():
                old_content = target_file.read_text(encoding="utf-8")
                if old_content == new_content:
                    continue
                diff = difflib.unified_diff(
                    old_content.splitlines(keepends=True),
                    new_content.splitlines(keepends=True),
                    fromfile=f"a/{rel_path}",
                    tofile=f"b/{rel_path} (generated)",
                )
                print("".join(diff))
            else:
                print(f"--- /dev/null")
                print(f"+++ b/{rel_path} (new)")
                for line in new_content.splitlines():
                    print(f"+{line}")
