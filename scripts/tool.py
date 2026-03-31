#!/usr/bin/env python3
"""
tool.py — Central dispatcher for the CppCmakeProjectTemplate toolset.

Routes commands to:
- Core Modules:  scripts/core/commands/
- Plugin Modules: scripts/plugins/
"""

import sys
import argparse
import importlib
import pkgutil
from pathlib import Path

# Setup paths
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from core.utils.common import Logger, GlobalConfig, load_session

# Core command to sub-package mapping
CORE_COMMANDS = {
    "build": "core.commands.build",
    "lib":   "core.commands.lib",
    "release": "core.commands.release",
    "sol":   "core.commands.sol",
    "security": "core.commands.security",
    "tui":   "tui",  # scripts/tui.py
    "session": "core.commands.session",
    "plugins": "core.commands.plugins",
}

def discover_plugins():
    """Scan scripts/plugins/ for module files."""
    plugins = {}
    plugin_dir = SCRIPTS_DIR / "plugins"
    if plugin_dir.exists():
        for finder, name, ispkg in pkgutil.iter_modules([str(plugin_dir)]):
            plugins[name] = f"plugins.{name}"
    return plugins

def main():
    parser = argparse.ArgumentParser(prog="tool", add_help=False)
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--json",    action="store_true")
    parser.add_argument("--yes",     action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--help",    action="store_true")
    parser.add_argument("--version", action="store_true")

    # Separate globals from command
    tool_args = []
    cmd_and_beyond = []
    for i, arg in enumerate(sys.argv[1:]):
        if not arg.startswith("-"):
            cmd_and_beyond = sys.argv[i+1:]
            break
        tool_args.append(arg)
    # Load session (fallback values) and parse tool globals
    session = load_session() or {}
    args = parser.parse_args(tool_args)
    if args.help:
        print_main_help()
        sys.exit(0)

    # Detect which flags were provided on the CLI so we can give CLI precedence
    provided = {a.split('=')[0] for a in tool_args}

    GlobalConfig.VERBOSE = args.verbose if '--verbose' in provided else bool(session.get('verbose', args.verbose))
    GlobalConfig.JSON    = args.json    if '--json'    in provided else bool(session.get('json', args.json))
    GlobalConfig.YES     = args.yes     if '--yes'     in provided else bool(session.get('yes', args.yes))
    GlobalConfig.DRY_RUN = args.dry_run if '--dry-run' in provided else bool(session.get('dry_run', args.dry_run))

    # If no command was provided on CLI, fall back to session default_command when present
    if not cmd_and_beyond:
        if args.version:
            print(f"Toolset v{GlobalConfig.VERSION}")
            sys.exit(0)
        default_cmd = session.get('default_command')
        if default_cmd:
            # default_command stored as a string like: "build check"
            cmd_and_beyond = default_cmd.split()
        else:
            print_main_help()
            sys.exit(0)

    command = cmd_and_beyond[0]
    remaining = cmd_and_beyond[1:]

    # 1. Look in CORE
    module_name = CORE_COMMANDS.get(command)

    # 2. Look in PLUGINS
    if not module_name:
        plugins = discover_plugins()
        module_name = plugins.get(command)

    if not module_name:
        Logger.error(f"Unknown command: {command}")
        sys.exit(1)

    # Lazy import and execute
    try:
        Logger.debug(f"Dispatcher: {command} -> {module_name}")
        module = importlib.import_module(module_name)
        if hasattr(module, "main"):
            module.main(remaining)
        else:
            Logger.error(f"Module {module_name} missing main()")
            sys.exit(1)
    except SystemExit as e:
        sys.exit(e.code)
    except Exception as e:
        Logger.error(f"Unexpected error: {e}")
        if GlobalConfig.VERBOSE:
            import traceback
            traceback.print_exc()
        sys.exit(1)

def print_main_help():
    print("""CppCmakeProjectTemplate Unified CLI

Usage: tool [globals] <command> [args...]

Global Options:
  --verbose    Enable debug logging
  --json       Output results in JSON
  --yes        Auto-confirm (non-interactive)
  --dry-run    Preview only
  --version    Show version
  --help       Show this help

Core Commands:
  build        Configure, compile, test, extension (.vsix)
  lib          Library CRUD (add/remove/rename/move/deps/export/info/test)
  sol          Presets, toolchains, repo, CI, upgrade-std, doctor
  tui          Terminal UI (interactive wrapper)
    plugins      List and inspect available `scripts/plugins/` modules

Plugins (scripts/plugins/):
  setup        Check/install project dependencies
  init         Rename project after clone
  hooks        Install git pre-commit hooks
  hello        Example plugin

Examples:
  tool build check
  tool lib add my_lib --template singleton
  tool lib deps my_lib --add-url https://github.com/fmtlib/fmt@10.2.1
  tool sol ci --preset-filter gcc
  tool tui
  tool setup --install
  tool init --name MyProject
""")

if __name__ == "__main__":
    main()
