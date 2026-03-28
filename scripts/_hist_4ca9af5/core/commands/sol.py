#!/usr/bin/env python3
"""
core/commands/sol.py — Project orchestration façade.

Imports functions directly from scripts/toolsolution.py — no subprocess.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# ── Path bootstrap ────────────────────────────────────────────────────────────
_SCRIPTS = Path(__file__).resolve().parent.parent.parent  # scripts/
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

# Import real implementation (no subprocess)
import toolsolution as _sol  # scripts/toolsolution.py

from core.utils.common import Logger, GlobalConfig, CLIResult


# ── Thin wrappers ─────────────────────────────────────────────────────────────

def _wrap(fn, args) -> CLIResult:
    """Run a toolsolution cmd_* function, catch SystemExit."""
    try:
        fn(args)
        return CLIResult(success=True)
    except SystemExit as e:
        return CLIResult(success=(e.code == 0), code=e.code or 1)


def cmd_target_list(args):    return _wrap(_sol.cmd_target_list,    args)
def cmd_target_build(args):   return _wrap(_sol.cmd_target_build,   args)
def cmd_preset_list(args):    return _wrap(_sol.cmd_preset_list,    args)
def cmd_preset_add(args):     return _wrap(_sol.cmd_preset_add,     args)
def cmd_preset_remove(args):  return _wrap(_sol.cmd_preset_remove,  args)
def cmd_toolchain_list(args): return _wrap(_sol.cmd_toolchain_list, args)
def cmd_toolchain_add(args):  return _wrap(_sol.cmd_toolchain_add,  args)
def cmd_toolchain_remove(args): return _wrap(_sol.cmd_toolchain_remove, args)
def cmd_config_get(args):     return _wrap(_sol.cmd_config_get,     args)
def cmd_config_set(args):     return _wrap(_sol.cmd_config_set,     args)
def cmd_doctor(args):         return _wrap(_sol.cmd_doctor,         args)
def cmd_test_run(args):       return _wrap(_sol.cmd_test_run,       args)
def cmd_upgrade_std(args):    return _wrap(_sol.cmd_upgrade_std,    args)
def cmd_repo_list(args):      return _wrap(_sol.cmd_repo_list,      args)
def cmd_repo_add_submodule(args): return _wrap(_sol.cmd_repo_add_submodule, args)
def cmd_repo_add_fetch(args): return _wrap(_sol.cmd_repo_add_fetch, args)
def cmd_repo_sync(args):      return _wrap(_sol.cmd_repo_sync,      args)
def cmd_repo_versions(args):  return _wrap(_sol.cmd_repo_versions,  args)
def cmd_ci(args):             return _wrap(_sol.cmd_ci,             args)


# ── Parser (mirrors scripts/toolsolution.py build_parser) ────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tool sol",
        description="Project orchestration (presets, toolchains, repo, CI, config, tests)",
    )
    sub = parser.add_subparsers(dest="subcommand", required=True)

    # ── target ────────────────────────────────────────────────────────────────
    tgt = sub.add_parser("target", help="Manage build targets")
    tgt_sub = tgt.add_subparsers(dest="action", required=True)
    tgt_sub.add_parser("list").set_defaults(func=cmd_target_list)
    p = tgt_sub.add_parser("build")
    p.add_argument("name")
    p.add_argument("--preset", default=None)
    p.set_defaults(func=cmd_target_build)

    # ── preset ────────────────────────────────────────────────────────────────
    pre = sub.add_parser("preset", help="Manage CMake presets")
    pre_sub = pre.add_subparsers(dest="action", required=True)
    pre_sub.add_parser("list").set_defaults(func=cmd_preset_list)
    p = pre_sub.add_parser("add")
    p.add_argument("--compiler", required=True)
    p.add_argument("--type",     required=True)
    p.add_argument("--link",     required=True)
    p.add_argument("--arch",     default="x86_64")
    p.add_argument("--name",     default=None)
    p.set_defaults(func=cmd_preset_add)
    p = pre_sub.add_parser("remove")
    p.add_argument("name")
    p.set_defaults(func=cmd_preset_remove)

    # ── toolchain ─────────────────────────────────────────────────────────────
    tc = sub.add_parser("toolchain", help="Manage toolchains")
    tc_sub = tc.add_subparsers(dest="action", required=True)
    tc_sub.add_parser("list").set_defaults(func=cmd_toolchain_list)
    p = tc_sub.add_parser("add")
    p.add_argument("--name",       required=True)
    p.add_argument("--template",   required=True)
    p.add_argument("--prefix",     default="")
    p.add_argument("--cpu",        default="")
    p.add_argument("--fpu",        default="")
    p.add_argument("--gen-preset", action="store_true", dest="gen_preset")
    p.set_defaults(func=cmd_toolchain_add)
    p = tc_sub.add_parser("remove")
    p.add_argument("name")
    p.set_defaults(func=cmd_toolchain_remove)

    # ── config ────────────────────────────────────────────────────────────────
    cfg = sub.add_parser("config", help="Project-wide config")
    cfg_sub = cfg.add_subparsers(dest="action", required=True)
    p = cfg_sub.add_parser("get")
    p.add_argument("key", nargs="?", default=None)
    p.set_defaults(func=cmd_config_get)
    p = cfg_sub.add_parser("set")
    p.add_argument("key")
    p.add_argument("value")
    p.set_defaults(func=cmd_config_set)

    # ── test ──────────────────────────────────────────────────────────────────
    p = sub.add_parser("test", help="Run tests (all or single target)")
    p.add_argument("target", nargs="?", default=None)
    p.add_argument("--preset", default=None)
    p.set_defaults(func=cmd_test_run)

    # ── upgrade-std ───────────────────────────────────────────────────────────
    p = sub.add_parser("upgrade-std", help="Set C++ standard solution-wide or per-lib")
    p.add_argument("--std",    required=True, choices=["14", "17", "20", "23"])
    p.add_argument("--target", default=None)
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_upgrade_std)

    # ── repo ──────────────────────────────────────────────────────────────────
    repo = sub.add_parser("repo", help="Multi-repo management")
    repo_sub = repo.add_subparsers(dest="action", required=True)
    repo_sub.add_parser("list").set_defaults(func=cmd_repo_list)
    repo_sub.add_parser("versions").set_defaults(func=cmd_repo_versions)
    repo_sub.add_parser("sync").set_defaults(func=cmd_repo_sync)
    p = repo_sub.add_parser("add-submodule")
    p.add_argument("--url",    required=True)
    p.add_argument("--dest",   required=True)
    p.add_argument("--branch", default="main")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_repo_add_submodule)
    p = repo_sub.add_parser("add-fetch")
    p.add_argument("--name",   required=True)
    p.add_argument("--url",    required=True)
    p.add_argument("--tag",    default="main")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_repo_add_fetch)

    # ── ci ────────────────────────────────────────────────────────────────────
    p = sub.add_parser("ci", help="CI pipeline simulation")
    p.add_argument("--preset-filter", default="", dest="preset_filter")
    p.add_argument("--fail-fast",     action="store_true", dest="fail_fast")
    p.set_defaults(func=cmd_ci)

    # ── doctor ────────────────────────────────────────────────────────────────
    sub.add_parser("doctor", help="Full project health check").set_defaults(func=cmd_doctor)

    return parser


def main(argv: list[str]) -> None:
    # Legacy: toolsolution --lib <args> delegation
    if argv and argv[0] == "--lib":
        import core.commands.lib as _lib_cmd
        return _lib_cmd.main(argv[1:])

    parser = build_parser()
    args = parser.parse_args(argv)
    if hasattr(args, "func"):
        args.func(args).exit()
    else:
        parser.print_help()
