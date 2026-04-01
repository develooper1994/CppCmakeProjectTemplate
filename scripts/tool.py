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
    "build":    "core.commands.build",
    "deps":     "core.commands.deps",
    "doc":      "core.commands.doc",
    "format":   "core.commands.format",
    "lib":      "core.commands.lib",
    "perf":     "core.commands.perf",
    "presets":  "core.commands.presets",
    "release":  "core.commands.release",
    "security": "core.commands.security",
    "session":  "core.commands.session",
    "sol":      "core.commands.sol",
    "plugins":  "core.commands.plugins",
    "tui":      "tui",  # scripts/tui.py
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
    parser.add_argument("--install", action="store_true", help="Provision/install required tools/deps for scripts")
    parser.add_argument("--recreate", action="store_true", help="When used with --install, recreate virtualenvs")
    parser.add_argument("--skip-ci", action="store_true", help="Skip CI-only steps (for local debug runs)")
    parser.add_argument("--ci-mode", choices=["smoke", "full", "nightly"], default=None,
                        help="CI run mode: smoke (fast), full (default), nightly (extended)")
    parser.add_argument("--report-artifact", default=None, metavar="PATH",
                        help="Path to write CI report artifact")
    parser.add_argument("--retain-days", type=int, default=None, metavar="N",
                        help="Artifact retention policy in days (for CI metadata)")
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
    GlobalConfig.INSTALL = args.install if '--install' in provided else bool(session.get('install', args.install))
    GlobalConfig.INSTALL_RECREATE = args.recreate if '--recreate' in provided else bool(session.get('install_recreate', args.recreate))
    GlobalConfig.SKIP_CI = getattr(args, 'skip_ci', False)
    GlobalConfig.CI_MODE = getattr(args, 'ci_mode', None)
    GlobalConfig.REPORT_ARTIFACT = getattr(args, 'report_artifact', None)
    GlobalConfig.RETAIN_DAYS = getattr(args, 'retain_days', None)

    # Apply tool.toml defaults (CLI values set above take precedence)
    try:
        from core.utils.config_loader import apply_to_global_config
        apply_to_global_config()
    except Exception:
        pass  # tool.toml is optional — never block execution

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
  --verbose              Enable debug logging
  --json                 Output results in JSON
  --yes                  Auto-confirm (non-interactive)
  --dry-run              Preview only
  --skip-ci              Skip CI-only steps (local debug)
  --ci-mode <mode>       CI run mode: smoke | full | nightly
  --report-artifact PATH Write CI report to path
  --retain-days N        Artifact retention days (CI metadata)
  --version              Show version
  --help                 Show this help

Core Commands:
  build        Configure, compile, test, extension (.vsix)
               Flags: --preset, --profile, --lto, --pgo, --sanitizers
  deps         Dependency management (lock, verify, list, conan-profile)
               Subcommands: lock, verify, list, conan-profile generate
  doc          Documentation utilities
               Subcommands: serve [--port N] [--open], list, build
  format       Code formatting and clang-tidy
               Subcommands: check, tidy-fix [--dry-run] [--apply], iwyu
  lib          Library CRUD (add/remove/rename/move/deps/export/info/test)
               Subcommands: add, remove, rename, move, list, tree, info, deps, export, doctor
  perf         Performance analysis and optimization
               Subcommands: size, build-time, track, check-budget, bench, valgrind, graph
  presets      Generate and manage CMakePresets.json
               Subcommands: generate, list, validate
  release      Version management and release tagging
               Subcommands: bump, set, set-revision, tag, publish, unpublish
  security     Security scanning (CVE, cppcheck, clang-tidy security checks)
               Flags: --format json|text, --fail-on-severity, --suppressions
  session      Persistent session state (preset, last command)
  sol          Project orchestration (presets, toolchains, CI, doctor)
               Subcommands: preset, ci, doctor, target, upgrade-std
  tui          Terminal UI — interactive wrapper for all tool commands
  plugins      List and inspect available plugins/

Plugins (scripts/plugins/):
  setup        Check/install project dependencies
  init         Rename project after clone
  hooks        Install git pre-commit hooks (pre-commit, gitleaks)
  hello        Example plugin

Examples:
  tool build check --no-sync          # Build + test (skip dependency sync)
  tool build --lto --profile hardened # Release build with LTO + hardening
  tool lib add my_lib --template singleton
  tool lib deps my_lib --add-url https://github.com/fmtlib/fmt@10.2.1
  tool perf track && tool perf check-budget
  tool perf bench --compare
  tool perf valgrind --binary build/gcc-debug-static-x86_64/apps/main_app/main_app
  tool perf graph --render --format svg
  tool doc serve --open
  tool doc list
  tool security --format json --fail-on-severity HIGH
  tool sol ci --preset-filter gcc
  tool tui
  tool setup --install
  tool init --name MyProject
""")

if __name__ == "__main__":
    main()
