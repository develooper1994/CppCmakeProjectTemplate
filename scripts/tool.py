#!/usr/bin/env python3
"""
tool.py — Modern C++ Project Orchestrator CLI.
Professional Proxy for CppCmakeProjectTemplate.
"""

import sys
import argparse
import importlib
import pkgutil
from pathlib import Path
from typing import Any, Dict

# Setup paths to ensure internal modules are discoverable
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from core.utils.common import Logger, GlobalConfig, load_session
from core.utils.config_loader import load_tool_config, apply_to_global_config

# Core command mapping
CORE_COMMANDS = {
    "build":    "core.commands.build",
    "deps":     "core.commands.deps",
    "doc":      "core.commands.doc",
    "format":   "core.commands.format",
    "generate": "core.commands.generate",
    "license":  "core.commands.license",
    "lib":      "core.commands.lib",
    "new":      "core.commands.new",
    "perf":     "core.commands.perf",
    "presets":  "core.commands.presets",
    "release":  "core.commands.release",
    "security": "core.commands.security",
    "session":  "core.commands.session",
    "sol":      "core.commands.sol",
    "validate":   "core.commands.validate",
    "completion": "core.commands.completion",
    "adopt":      "core.commands.adopt",
    "plugins":    "core.commands.plugins",
    "sbom":       "core.commands.sbom",
    "diagnostics": "core.commands.diagnostics",
    "nix":        "core.commands.nix",
    "migrate":    "core.commands.migrate",
    "templates":  "core.commands.templates",
    "tui":        "tui",
}

def discover_plugins() -> Dict[str, str]:
    """Scan scripts/plugins/ for additional commands."""
    plugins = {}
    plugin_dir = SCRIPTS_DIR / "plugins"
    if plugin_dir.exists():
        for _, name, _ in pkgutil.iter_modules([str(plugin_dir)]):
            plugins[name] = f"plugins.{name}"
    return plugins

def main():
    # 1. Global Parser
    parser = argparse.ArgumentParser(
        prog="tool",
        description="Unified CLI for C++ Project Management",
        add_help=False
    )

    # Global Flags
    globals = parser.add_argument_group("Global Options")
    globals.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    globals.add_argument("--json",    "-j", action="store_true", help="Output results in JSON format")
    globals.add_argument("--yes",     "-y", action="store_true", help="Auto-confirm all prompts")
    globals.add_argument("--dry-run", "-d", action="store_true", help="Preview changes without applying")
    globals.add_argument("--version",       action="store_true", help="Show tool version")
    globals.add_argument("--about",         action="store_true", help="About this project")
    globals.add_argument("--help",    "-h", action="store_true", help="Show this help message")

    # Capture global flags — only consider options appearing before the
    # first positional token (the subcommand).  This keeps `tool build --help`
    # from being treated as a top-level `--help` request.
    raw_args = sys.argv[1:]
    first_pos = next((i for i, t in enumerate(raw_args) if not t.startswith("-")), len(raw_args))
    prefix = raw_args[:first_pos]
    remaining = raw_args[first_pos:]

    global_args, leftover = parser.parse_known_args(prefix)

    # Build a combined token stream consisting of unknown prefix tokens
    # followed by the remaining tokens. Search this combined list for the
    # first token that maps to a known subcommand (optionally prefixed
    # with dashes). If found, treat that token as the command and forward
    # any tokens before it to the subcommand. This makes `tool --foo build`
    # behave like `tool build --foo` (so the build subparser sees `--foo`).
    combined = leftover + remaining

    # Dynamic Root Discovery
    try:
        from core.utils import common
        from core.utils.common import find_project_root
        local_root = find_project_root(Path.cwd())
        common.PROJECT_ROOT = local_root
    except Exception:
        pass

    # Global State Initialization
    session = load_session() or {}
    GlobalConfig.VERBOSE = global_args.verbose or bool(session.get('verbose', False))
    GlobalConfig.JSON    = global_args.json    or bool(session.get('json', False))
    GlobalConfig.YES     = global_args.yes     or bool(session.get('yes', False))
    GlobalConfig.DRY_RUN = global_args.dry_run or bool(session.get('dry_run', False))

    apply_to_global_config()

    # --version
    if global_args.version:
        print(f"Toolset v{GlobalConfig.VERSION}")
        sys.exit(0)

    # --about
    if global_args.about:
        print_about()
        sys.exit(0)

    all_commands = {**CORE_COMMANDS, **discover_plugins()}

    # Find the first token in the combined stream that maps to a known
    # subcommand. If found, that token is the command and any tokens
    # before it are forwarded as args to the subcommand parser.
    command = None
    cmd_args = []
    for idx, tok in enumerate(combined):
        name = tok.lstrip("-")
        if name in all_commands:
            command = name
            cmd_args = combined[:idx] + combined[idx+1:]
            break

    # If we didn't find a command in the combined stream, fall back to the
    # conventional remaining-first behavior (e.g. `tool build ...`).
    if command is None:
        if remaining and remaining[0].lstrip("-") in all_commands:
            command = remaining[0].lstrip("-")
            cmd_args = remaining[1:]
        else:
            # No subcommand detected.
            if global_args.help or not combined:
                print_main_help(parser)
                sys.exit(0)
            # Show an unknown command error for the first token.
            candidate = combined[0]
            Logger.error(f"Unknown command: '{candidate}'")
            sys.exit(1)

    # Resolve and Execute
    all_commands = {**CORE_COMMANDS, **discover_plugins()}
    module_path = all_commands.get(command)

    if not module_path:
        Logger.error(f"Unknown command: '{command}'")
        sys.exit(1)

    try:
        module = importlib.import_module(module_path)
        if hasattr(module, "main"):
            # If the user supplied a help flag in the prefix together with a
            # `--<command>` token (e.g. `tool --build --help`), move the help
            # token into the subcommand args so the subcommand shows its help
            # instead of the top-level help being used.
            try:
                prefix_help = any(t in ("-h", "--help") for t in prefix)
            except Exception:
                prefix_help = False
            if global_args.help and prefix_help and (command in all_commands):
                if not any(a in ("-h", "--help") for a in cmd_args):
                    cmd_args = ["--help"] + cmd_args

            # Sub-commands get only their specific arguments (like --help or build)
            module.main(cmd_args)
        else:
            Logger.error(f"Module '{module_path}' is missing a main() function.")
            sys.exit(1)
    except SystemExit as e:
        sys.exit(e.code)
    except Exception as e:
        Logger.error(f"Execution failed: {e}")
        if GlobalConfig.VERBOSE:
            import traceback
            traceback.print_exc()
        sys.exit(1)

def print_main_help(parser):
    parser.print_help()
    print("\nAvailable Commands:")
    all_cmds = {**CORE_COMMANDS, **discover_plugins()}
    for cmd in sorted(all_cmds.keys()):
        print(f"  {cmd:<12} (run 'tool {cmd} --help' for details)")

def print_about():
    print("""
CppCmakeProjectTemplate — Professional C++ Scaffolding & Tooling
================================================================

A generative, declarative C++ project orchestrator that bridges the gap
between high-level configuration (tool.toml) and low-level CMake build systems.

Vision: Only 'scripts/' and 'tool.toml' are hand-maintained.
        Everything else is an artifact.

Author: develooper1994
License: MIT
Repository: https://github.com/develooper1994/CppCmakeProjectTemplate
""")

if __name__ == "__main__":
    main()
