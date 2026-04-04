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
    # 1. Global Parser — Only for global flags that affect all commands
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
    globals.add_argument("--help",    "-h", action="store_true", help="Show this help message")

    # Capture global flags and separate the command
    global_args, remaining = parser.parse_known_args()

    # Dynamic Root Discovery
    try:
        from core.utils.common import find_project_root
        local_root = find_project_root(Path.cwd())
        from core.utils import common
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

    if global_args.version:
        print(f"Toolset v{GlobalConfig.VERSION}")
        sys.exit(0)

    if global_args.help and not remaining:
        parser.print_help()
        print("\nAvailable Commands:")
        all_cmds = {**CORE_COMMANDS, **discover_plugins()}
        for cmd in sorted(all_cmds.keys()):
            print(f"  {cmd:<12} (run 'tool {cmd} --help' for details)")
        sys.exit(0)

    # Command Selection
    if not remaining:
        default_cmd = session.get('default_command')
        if default_cmd:
            remaining = default_cmd.split()
        else:
            parser.print_help()
            sys.exit(0)

    command = remaining[0]
    cmd_args = remaining[1:]

    # Resolve and Execute
    all_commands = {**CORE_COMMANDS, **discover_plugins()}
    module_path = all_commands.get(command)

    if not module_path:
        Logger.error(f"Unknown command: '{command}'")
        sys.exit(1)

    try:
        module = importlib.import_module(module_path)
        if hasattr(module, "main"):
            # Sub-commands get only their specific arguments
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

if __name__ == "__main__":
    main()
