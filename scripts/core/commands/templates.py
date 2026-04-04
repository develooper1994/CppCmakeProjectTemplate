"""
core/commands/templates.py — Project templates gallery
=======================================================

Curated starter templates selectable via the wizard or CLI.

Usage:
  tool templates list                    # list available templates
  tool templates create <name> [--template <tpl>] [--target-dir DIR]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from core.utils.common import Logger, CLIResult, PROJECT_ROOT

COMMAND_META = {
    "name": "templates",
    "description": "Project templates gallery — curated starter configurations",
}

# ---------------------------------------------------------------------------
# Template definitions
# ---------------------------------------------------------------------------

TEMPLATES: dict[str, dict] = {
    "minimal": {
        "description": "Bare-bones C++ project — single library, single app",
        "profile": "minimal",
        "config": {
            "project": {
                "libs": [{"name": "core", "type": "normal", "description": "Core library"}],
                "apps": [{"name": "main", "description": "Main application", "deps": ["core"]}],
            },
            "generate": {"profile": "minimal"},
        },
    },
    "library": {
        "description": "Reusable C++ library — find_package() support, docs, CI",
        "profile": "library",
        "config": {
            "project": {
                "libs": [
                    {"name": "mylib", "type": "normal", "description": "Public API library"},
                ],
                "apps": [],
            },
            "generate": {"profile": "library"},
        },
    },
    "application": {
        "description": "Complete application — multiple libs, CLI app, CI/CD",
        "profile": "app",
        "config": {
            "project": {
                "libs": [
                    {"name": "core", "type": "normal", "description": "Core logic"},
                    {"name": "utils", "type": "normal", "description": "Utility functions"},
                ],
                "apps": [
                    {"name": "app", "description": "Main application", "deps": ["core", "utils"]},
                ],
            },
            "generate": {"profile": "app"},
        },
    },
    "embedded": {
        "description": "Embedded/bare-metal — cross-compilation toolchains, no OS",
        "profile": "embedded",
        "config": {
            "project": {
                "libs": [
                    {"name": "hal", "type": "normal", "description": "Hardware abstraction layer"},
                    {"name": "drivers", "type": "normal", "description": "Device drivers"},
                ],
                "apps": [
                    {"name": "firmware", "description": "Firmware binary", "deps": ["hal", "drivers"]},
                ],
            },
            "presets": {
                "compilers": ["gcc"],
                "arches": ["arm-none-eabi"],
                "linkages": ["static"],
            },
            "generate": {"profile": "embedded"},
        },
    },
    "networking": {
        "description": "Networking library — async I/O, protocol buffers, benchmarks",
        "profile": "full",
        "config": {
            "project": {
                "libs": [
                    {"name": "net_core", "type": "normal", "description": "Networking core"},
                    {"name": "protocol", "type": "normal", "description": "Protocol implementation"},
                ],
                "apps": [
                    {"name": "server", "description": "Example server", "deps": ["net_core", "protocol"]},
                    {"name": "client", "description": "Example client", "deps": ["net_core", "protocol"]},
                ],
            },
            "generate": {"profile": "full"},
        },
    },
    "header-only": {
        "description": "Header-only library — zero build deps, easy integration",
        "profile": "library",
        "config": {
            "project": {
                "libs": [
                    {"name": "mylib", "type": "header-only", "description": "Header-only library"},
                ],
                "apps": [],
            },
            "generate": {"profile": "library"},
        },
    },
    "game-engine": {
        "description": "Game engine scaffold — rendering, ECS, asset pipeline",
        "profile": "full",
        "config": {
            "project": {
                "libs": [
                    {"name": "engine_core", "type": "normal", "description": "Engine core loop"},
                    {"name": "renderer", "type": "normal", "description": "Rendering backend"},
                    {"name": "ecs", "type": "normal", "description": "Entity Component System"},
                    {"name": "assets", "type": "normal", "description": "Asset pipeline"},
                ],
                "apps": [
                    {"name": "editor", "description": "Level editor",
                     "deps": ["engine_core", "renderer", "ecs", "assets"]},
                    {"name": "runtime", "description": "Game runtime",
                     "deps": ["engine_core", "renderer", "ecs", "assets"]},
                ],
            },
            "generate": {"profile": "full"},
        },
    },
}


def _list_templates() -> None:
    """Print available templates."""
    print("\nAvailable project templates:\n")
    for name, tpl in TEMPLATES.items():
        libs = tpl["config"].get("project", {}).get("libs", [])
        apps = tpl["config"].get("project", {}).get("apps", [])
        print(f"  \033[1m{name:<16}\033[0m {tpl['description']}")
        print(f"  {'':16} Profile: {tpl['profile']}, "
              f"Libs: {len(libs)}, Apps: {len(apps)}")
        print()


def _create_from_template(
    project_name: str,
    template_name: str,
    target_dir: Path,
    dry_run: bool = False,
) -> None:
    """Generate a project from a template."""
    if template_name not in TEMPLATES:
        Logger.error(f"Unknown template: {template_name}")
        Logger.info(f"Available: {', '.join(TEMPLATES.keys())}")
        sys.exit(1)

    tpl = TEMPLATES[template_name]
    Logger.info(f"Using template: {template_name} — {tpl['description']}")

    # Build config from template
    from copy import deepcopy
    config = deepcopy(tpl["config"])
    config.setdefault("project", {})["name"] = project_name

    # CORRECT: Profile belongs in [generate], not [project]
    config.setdefault("generate", {})["profile"] = tpl["profile"]

    if dry_run:
        Logger.info("[DRY-RUN] Would generate:")
        print(json.dumps(config, indent=2))
        return

    from core.generator.engine import generate
    from core.generator.merge import ConflictPolicy

    result = generate(
        target_dir=target_dir,
        policy=ConflictPolicy.OVERWRITE,
        config=config,
    )

    if result.errors:
        Logger.error(f"Template creation had {len(result.errors)} error(s):")
        for err in result.errors:
            Logger.error(f"  {err}")
    else:
        Logger.success(f"Created '{project_name}' from '{template_name}' template: {result.summary()}")


def main(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(
        prog="tool templates",
        description="Project templates gallery",
    )
    sub = parser.add_subparsers(dest="subcommand")

    # list
    sub.add_parser("list", help="List available templates")

    # create
    create = sub.add_parser("create", help="Create project from template")
    create.add_argument("name", nargs="?", default=None, help="Project name")
    create.add_argument("--template", "-t", default="minimal",
                        choices=list(TEMPLATES.keys()),
                        help="Template to use (default: minimal)")
    create.add_argument("--target-dir", default=None,
                        help="Output directory (default: ./<name>)")
    create.add_argument("--dry-run", action="store_true",
                        help="Preview without writing files")

    args = parser.parse_args(argv)

    if args.subcommand == "list" or not args.subcommand:
        _list_templates()
    elif args.subcommand == "create":
        # If name is not provided but target-dir is, use target-dir's name
        name = args.name
        target = Path(args.target_dir) if args.target_dir else (Path(name) if name else Path.cwd())
        if not name:
            name = target.name

        if not name or name == ".":
            Logger.error("Project name required (either as argument or inferred from target-dir)")
            sys.exit(1)

        _create_from_template(name, args.template, target, args.dry_run)
