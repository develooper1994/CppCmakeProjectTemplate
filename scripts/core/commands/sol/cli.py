"""CLI parser and entry point for `tool sol`."""
from __future__ import annotations

import argparse

from .targets import (
    cmd_target_list,
    cmd_target_build,
    cmd_target_add,
    cmd_preset_list,
    cmd_preset_add,
    cmd_preset_remove,
)
from .toolchains import (
    cmd_toolchain_list,
    cmd_toolchain_add,
    cmd_toolchain_remove,
    cmd_sysroot_add,
    _cmd_sysroot_list,
)
from .project import (
    cmd_config_get,
    cmd_config_set,
    cmd_doctor,
    cmd_test_run,
    cmd_upgrade_std,
    cmd_check_extra,
    cmd_init_skeleton,
    cmd_ci,
    cmd_cmake_version,
    cmd_clangd,
)
from .repo import (
    cmd_repo_list,
    cmd_repo_add_submodule,
    cmd_repo_add_fetch,
    cmd_repo_sync,
    cmd_repo_versions,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tool sol",
        description="Project orchestration (presets, toolchains, repo, CI, config, tests)",
    )
    sub = parser.add_subparsers(dest="subcommand", required=True)

    # target
    tgt = sub.add_parser("target", help="Manage build targets")
    tgt_sub = tgt.add_subparsers(dest="action", required=True)
    tgt_sub.add_parser("list").set_defaults(func=cmd_target_list)
    p = tgt_sub.add_parser("build")
    p.add_argument("name")
    p.add_argument("--preset", default=None)
    p.set_defaults(func=cmd_target_build)
    p = tgt_sub.add_parser("add")
    p.add_argument("name")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_target_add)

    # preset
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

    # toolchain
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

    # config
    cfg = sub.add_parser("config", help="Project-wide config")
    cfg_sub = cfg.add_subparsers(dest="action", required=True)
    p = cfg_sub.add_parser("get")
    p.add_argument("key", nargs="?", default=None)
    p.set_defaults(func=cmd_config_get)
    p = cfg_sub.add_parser("set")
    p.add_argument("key")
    p.add_argument("value")
    p.set_defaults(func=cmd_config_set)

    # test
    p = sub.add_parser("test", help="Run tests (all or single target)")
    p.add_argument("target", nargs="?", default=None)
    p.add_argument("--preset", default=None)
    p.set_defaults(func=cmd_test_run)

    # upgrade-std
    p = sub.add_parser("upgrade-std", help="Set C++ standard solution-wide or per-lib")
    p.add_argument("--std",    required=True, choices=["14", "17", "20", "23"])
    p.add_argument("--target", default=None)
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_upgrade_std)

    # repo
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

    # ci
    p = sub.add_parser("ci", help="CI pipeline simulation")
    p.add_argument("--preset-filter", default="", dest="preset_filter")
    p.add_argument("--fail-fast",     action="store_true", dest="fail_fast")
    p.set_defaults(func=cmd_ci)

    # check-extra
    sub.add_parser("check-extra", help="Run ruff, mypy, cppcheck").set_defaults(func=cmd_check_extra)

    # init-skeleton
    p = sub.add_parser("init-skeleton", help="Regenerate project CMake structure from templates")
    p.add_argument("--name", help="New project name")
    p.add_argument("--version", help="New project version")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_init_skeleton)

    # doctor
    sub.add_parser("doctor", help="Full project health check").set_defaults(func=cmd_doctor)

    # cmake-version
    cv = sub.add_parser("cmake-version",
                        help="Detect or globally set cmake_minimum_required VERSION")
    cv_sub = cv.add_subparsers(dest="cmake_action", required=True)
    cv_sub.add_parser("detect",
                      help="Show installed CMake version and project minimum"
                      ).set_defaults(func=cmd_cmake_version)
    p = cv_sub.add_parser("set",
                           help="Update cmake_minimum_required in all CMakeLists.txt")
    p.add_argument("version", help="Target VERSION string, e.g. '3.25' or '3.28'")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_cmake_version)

    # clangd
    p = sub.add_parser("clangd",
                        help="Generate a .clangd config from compile_commands.json")
    p.add_argument("--dry-run", action="store_true",
                   help="Print generated .clangd content without writing")
    p.set_defaults(func=cmd_clangd)

    # sysroot
    sysroot = sub.add_parser("sysroot", help="Cross-compile sysroot management")
    sys_sub = sysroot.add_subparsers(dest="sysroot_action", required=True)
    p = sys_sub.add_parser("add", help="Download/install a sysroot and register it for CMake")
    p.add_argument("arch", help="Target architecture (e.g. aarch64, armv7)")
    p.add_argument("--url", default=None,
                   help="URL of a sysroot tarball to download (optional; omit to use apt/package manager)")
    p.add_argument("--dry-run", action="store_true", dest="dry_run",
                   help="Preview changes without writing anything")
    p.set_defaults(func=cmd_sysroot_add)
    p = sys_sub.add_parser("list", help="List registered sysroots")
    p.set_defaults(func=lambda a: _cmd_sysroot_list())
    sysroot.set_defaults(func=lambda a: sysroot.print_help())

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
