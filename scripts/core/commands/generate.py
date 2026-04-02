"""
core/commands/generate.py — `tool generate` CLI command.

Generates project files from tool.toml configuration.

Usage:
    tool generate                                         # regenerate all components
    tool generate --target-dir /path/to/dir               # generate into a new directory
    tool generate --profile minimal --without ci          # lighter output with feature toggles
    tool generate --component cmake-dynamic               # regenerate one component
    tool generate --dry-run                               # preview without writing
    tool generate --diff                                  # show diff against existing
    tool generate --merge                                 # use merge conflict resolution
    tool generate --force                                 # overwrite without asking
    tool generate --debug                                 # tracebacks + per-component timing
    tool generate --verbose                               # extra progress messages
    tool generate --json                                  # machine-readable JSON output
"""
from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from core.utils.common import Logger, GlobalConfig, PROJECT_ROOT


def _coerce_value(raw: str) -> Any:
    lowered = raw.lower()
    if lowered in {"true", "yes", "on"}:
        return True
    if lowered in {"false", "no", "off"}:
        return False
    if raw.isdigit():
        return int(raw)
    return raw


def _set_nested(config: dict[str, Any], dotted_key: str, value: Any) -> None:
    cursor = config
    parts = dotted_key.split(".")
    for part in parts[:-1]:
        cursor = cursor.setdefault(part, {})
    cursor[parts[-1]] = value


def _maybe_init_git(
    target_dir: Path,
    target_preexisted: bool,
    cfg: dict[str, Any],
    *,
    force_init: bool = False,
    skip_init: bool = False,
    dry_run: bool = False,
) -> None:
    if skip_init or dry_run:
        return
    if (target_dir / ".git").exists():
        return

    git_cfg = cfg.get("git", {})
    init_mode = str(git_cfg.get("init", "auto")).strip().lower()
    if force_init:
        init_mode = "always"

    should_init = init_mode == "always" or (init_mode == "auto" and not target_preexisted)
    if not should_init:
        return

    try:
        proc = subprocess.run(
            ["git", "init"],
            cwd=target_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        Logger.warn("git is not installed; skipping repository initialization.")
        return

    if proc.returncode == 0:
        Logger.success("Initialized git repository in target directory.")
    else:
        output = (proc.stdout or "").strip()
        Logger.warn(f"git init failed; generation still completed. {output}")


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
    parser.add_argument(
        "--list-profiles",
        action="store_true",
        default=False,
        help="List available generation profiles.",
    )
    parser.add_argument(
        "--profile",
        type=str,
        default=None,
        help="Generation profile override (e.g. full, minimal, library, app, embedded).",
    )
    parser.add_argument("--license", dest="license_name", type=str, default=None, help="Override the generated license SPDX id.")
    parser.add_argument("--author", type=str, default=None, help="Override the generated author metadata.")
    parser.add_argument("--contact", type=str, default=None, help="Override the generated contact metadata.")
    parser.add_argument("--set", action="append", default=[], metavar="KEY=VALUE", help="Override any config value, e.g. generate.profile=minimal")
    parser.add_argument("--with", dest="with_features", action="append", default=[], metavar="FEATURE", help="Enable an optional feature (repeatable).")
    parser.add_argument("--without", dest="without_features", action="append", default=[], metavar="FEATURE", help="Disable an optional feature (repeatable).")
    parser.add_argument("--explain", action="store_true", default=False, help="Show the effective profile and feature toggles before generating.")
    parser.add_argument("--init-git", action="store_true", default=False, help="Always initialize git in the target directory after generation.")
    parser.add_argument("--no-init-git", action="store_true", default=False, help="Do not initialize git even for a new target directory.")
    parser.add_argument("--interactive", "-i", action="store_true", default=False, help="Start the interactive project creation wizard.")
    parser.add_argument("--debug", action="store_true", default=False, help="Enable debug output: full tracebacks and per-component timing.")
    parser.add_argument("--verbose", "-v", action="store_true", default=False, help="Extra progress messages during generation.")
    parser.add_argument("--json", dest="json_output", action="store_true", default=False, help="Emit machine-readable JSON output instead of human text.")

    args = parser.parse_args(argv)

    # Use global dry-run if set
    dry_run = args.dry_run or GlobalConfig.DRY_RUN

    # Import generator lazily
    from core.generator.engine import (
        COMPONENT_REGISTRY,
        PROFILE_COMPONENTS,
        build_context,
        get_disabled_features,
        get_enabled_features,
        generate,
    )
    from core.generator.merge import ConflictPolicy
    from core.utils.config_loader import load_tool_config

    if args.list_components:
        Logger.info("Available generator components:")
        for name in sorted(COMPONENT_REGISTRY.keys()):
            mod_path, func = COMPONENT_REGISTRY[name]
            Logger.info(f"  {name:20s} → {mod_path}.{func}")
        return

    if args.list_profiles:
        Logger.info("Available generator profiles:")
        for name in sorted(PROFILE_COMPONENTS.keys()):
            components = ", ".join(PROFILE_COMPONENTS[name])
            Logger.info(f"  {name:10s} → {components}")
        return

    # Interactive wizard mode
    if args.interactive:
        from core.generator.wizard import Wizard
        wiz = Wizard(interactive=True)
        answers = wiz.run()
        cfg = copy.deepcopy(answers.to_config())

        # Allow CLI overrides on top of wizard answers
        if args.profile:
            cfg["generate"]["profile"] = args.profile
        if args.license_name:
            cfg["project"]["license"] = args.license_name
        if args.author is not None:
            cfg["project"]["author"] = args.author
        if args.contact is not None:
            cfg["project"]["contact"] = args.contact
        if args.with_features:
            cfg["generate"]["with"] = list(dict.fromkeys(args.with_features))
        if args.without_features:
            cfg["generate"]["without"] = list(dict.fromkeys(args.without_features))

        target_dir = args.target_dir or Path.cwd() / answers.name
        target_dir = Path(target_dir).resolve()
        target_preexisted = target_dir.exists()
        target_dir.mkdir(parents=True, exist_ok=True)

        policy = ConflictPolicy.OVERWRITE if args.force else None
        components = [args.component] if args.component else None

        Logger.info(f"Generating into: {target_dir}")
        result = generate(
            target_dir=target_dir,
            components=components,
            policy=policy or ConflictPolicy.OVERWRITE,
            dry_run=dry_run,
            config=cfg,
            debug=args.debug,
            verbose=args.verbose,
        )
        if args.json_output:
            _print_json(result)
        else:
            for f in result.created:
                Logger.success(f"  + {f}")
            for f in result.errors:
                Logger.error(f"  ✗ {f}")
            Logger.info(f"Done: {result.summary()}")

        if result.errors:
            sys.exit(1)
        _maybe_init_git(
            target_dir, target_preexisted, cfg,
            force_init=args.init_git,
            skip_init=args.no_init_git,
            dry_run=dry_run,
        )
        return

    # Resolve target directory
    target_dir = args.target_dir or PROJECT_ROOT
    target_dir = Path(target_dir).resolve()
    target_preexisted = target_dir.exists()
    target_dir.mkdir(parents=True, exist_ok=True)

    cfg = copy.deepcopy(load_tool_config())
    cfg.setdefault("project", {})
    cfg.setdefault("generate", {})
    cfg.setdefault("git", {})

    if args.profile:
        cfg["generate"]["profile"] = args.profile
    if args.license_name:
        cfg["project"]["license"] = args.license_name
    if args.author is not None:
        cfg["project"]["author"] = args.author
    if args.contact is not None:
        cfg["project"]["contact"] = args.contact
    if args.init_git:
        cfg["git"]["init"] = "always"
    if args.no_init_git:
        cfg["git"]["init"] = "never"
    if args.with_features:
        cfg["generate"]["with"] = list(dict.fromkeys(args.with_features))
    if args.without_features:
        cfg["generate"]["without"] = list(dict.fromkeys(args.without_features))

    for override in args.set:
        if "=" not in override:
            Logger.error(f"Invalid --set override: {override!r}. Expected KEY=VALUE.")
            sys.exit(2)
        key, value = override.split("=", 1)
        _set_nested(cfg, key.strip(), _coerce_value(value.strip()))

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
        _show_diff(target_dir, components, cfg)
        return

    if args.explain:
        ctx = build_context(cfg)
        enabled = ", ".join(sorted(get_enabled_features(ctx))) or "(none)"
        disabled = ", ".join(sorted(get_disabled_features(ctx))) or "(none)"
        Logger.info(f"Profile: {ctx.profile}")
        Logger.info(f"Explicitly enabled features: {enabled}")
        Logger.info(f"Disabled features: {disabled}")

    Logger.info(f"Generating into: {target_dir}")
    if dry_run:
        Logger.info("(dry-run mode — no files will be written)")

    result = generate(
        target_dir=target_dir,
        components=components,
        policy=policy,
        dry_run=dry_run,
        config=cfg,
        debug=args.debug,
        verbose=args.verbose,
    )

    # Report results
    if args.json_output:
        _print_json(result)
    else:
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
                Logger.warn(f"  ! {f}")
        if result.errors:
            for f in result.errors:
                Logger.error(f"  ✗ {f}")

        Logger.info(f"Done: {result.summary()}")

    if result.errors:
        sys.exit(1)

    _maybe_init_git(
        target_dir, target_preexisted, cfg,
        force_init=args.init_git,
        skip_init=args.no_init_git,
        dry_run=dry_run,
    )


def _print_json(result) -> None:
    """Emit a machine-readable JSON summary of the generation run."""
    data: dict[str, Any] = {
        "created": result.created,
        "written": result.written,
        "skipped": result.skipped,
        "conflicts": result.conflicts,
        "errors": result.errors,
        "summary": result.summary(),
    }
    if hasattr(result, "timings") and result.timings:
        data["timings"] = result.timings
    print(json.dumps(data, indent=2))


def _show_diff(target_dir: Path, components: list[str] | None, config: dict[str, Any] | None = None) -> None:
    """Show unified diff between existing files and what would be generated."""
    import difflib
    from core.generator.engine import generate, build_context, COMPONENT_REGISTRY

    ctx = build_context(config)
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
