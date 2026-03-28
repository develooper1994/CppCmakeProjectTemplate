#!/usr/bin/env python3
"""
core/commands/sol.py — Project orchestration implementation.

Implements commands that used to live in `scripts/toolsolution.py`.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

# ── Path bootstrap ────────────────────────────────────────────────────────────
_SCRIPTS = Path(__file__).resolve().parent.parent.parent  # scripts/
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from core.utils.common import (
    Logger,
    GlobalConfig,
    CLIResult,
    run_proc,
    PROJECT_ROOT,
    json_read_cached,
    json_cache_clear,
)
import json
import shutil
import re
import subprocess
from functools import lru_cache

TOOLCHAINS_DIR = PROJECT_ROOT / "cmake" / "toolchains"
PRESETS_FILE = PROJECT_ROOT / "CMakePresets.json"
FETCH_DEPS_FILE = PROJECT_ROOT / ".fetch_deps.json"


def load_presets() -> dict:
    if not PRESETS_FILE.exists():
        return {}
    try:
        data = json_read_cached(PRESETS_FILE, default={}) or {}
        return data
    except Exception:
        Logger.error("Failed to parse CMakePresets.json")
        raise


@lru_cache(maxsize=1)
def load_fetch_deps() -> list:
    if not FETCH_DEPS_FILE.exists():
        return []
    try:
        return json.loads(FETCH_DEPS_FILE.read_text(encoding="utf-8"))
    except Exception:
        Logger.error("Failed to parse .fetch_deps.json")
        return []


def save_presets(data: dict) -> None:
    PRESETS_FILE.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    try:
        json_cache_clear(PRESETS_FILE)
    except Exception:
        pass


VALID_COMPILERS = {"gcc", "clang", "msvc"}
VALID_TYPES = {"debug", "release", "relwithdebinfo"}
VALID_LINKS = {"static", "dynamic"}
_BUILD_TYPE = {"debug": "Debug", "release": "Release", "relwithdebinfo": "RelWithDebInfo"}
_SHARED = {"static": "OFF", "dynamic": "ON"}


def _make_preset_name(compiler: str, btype: str, link: str, arch: str) -> str:
    return f"{compiler}-{btype}-{link}-{arch}"



def _impl_cmd_target_list(args) -> None:
    root = PROJECT_ROOT
    apps = sorted([p.name for p in (root / "apps").iterdir()]) if (root / "apps").exists() else []
    libs = sorted([p.name for p in (root / "libs").iterdir()]) if (root / "libs").exists() else []
    print("Apps:")
    for a in apps:
        print(" -", a)
    print("Libraries:")
    for l in libs:
        print(" -", l)


def _impl_cmd_target_build(args) -> None:
    name = args.name
    preset = getattr(args, "preset", None) or "gcc-debug-static-x86_64"
    run_proc([sys.executable, str(PROJECT_ROOT / "scripts" / "tool.py"), "build", "--preset", preset])
    run_proc(["cmake", "--build", "--preset", preset, "--target", name])


def _impl_cmd_preset_list(args) -> None:
    run_proc(["cmake", "--list-presets"])


def _impl_cmd_preset_add(args) -> None:
    compiler = getattr(args, "compiler")
    btype = getattr(args, "type")
    link = getattr(args, "link")
    arch = getattr(args, "arch", "x86_64")
    name = getattr(args, "name", None)
    if compiler not in VALID_COMPILERS or btype not in VALID_TYPES or link not in VALID_LINKS:
        Logger.error("Invalid preset parameters")
        raise SystemExit(2)
    pname = name or _make_preset_name(compiler, btype, link, arch)
    data = load_presets()
    cfgs = data.setdefault("configurePresets", [])
    builds = data.setdefault("buildPresets", [])
    # Avoid duplicate
    if any(p.get("name") == pname for p in cfgs):
        Logger.warn(f"Preset {pname} already exists")
        return
    cfg = {
        "name": pname,
        "generator": "Ninja",
        "binaryDir": f"build/{pname}",
        "cacheVariables": {
            "CMAKE_BUILD_TYPE": _BUILD_TYPE.get(btype, "Debug"),
            "BUILD_SHARED_LIBS": _SHARED.get(link, "OFF"),
        },
    }
    cfgs.append(cfg)
    builds.append({"name": f"{pname}-build", "configurePreset": pname})
    save_presets(data)
    Logger.info(f"Added configure/build preset pair: {pname}")


def _impl_cmd_preset_remove(args) -> None:
    name = getattr(args, "name")
    data = load_presets()
    cfgs = data.get("configurePresets", [])
    builds = data.get("buildPresets", [])
    new_cfgs = [p for p in cfgs if p.get("name") != name]
    new_builds = [b for b in builds if b.get("configurePreset") != name]
    if len(new_cfgs) == len(cfgs):
        Logger.warn(f"Preset {name} not found")
        return
    data["configurePresets"] = new_cfgs
    data["buildPresets"] = new_builds
    save_presets(data)
    Logger.info(f"Removed preset {name} and associated build presets")


def _impl_cmd_toolchain_list(args) -> None:
    if not TOOLCHAINS_DIR.exists():
        print("No toolchains registered")
        return
    for p in sorted(TOOLCHAINS_DIR.iterdir()):
        if p.is_file():
            print(p.name)


def _impl_cmd_toolchain_add(args) -> None:
    name = getattr(args, "name")
    template = getattr(args, "template")
    prefix = getattr(args, "prefix", "")
    cpu = getattr(args, "cpu", "")
    fpu = getattr(args, "fpu", "")
    gen_preset = getattr(args, "gen_preset", False)
    TOOLCHAINS_DIR.mkdir(parents=True, exist_ok=True)
    dest = TOOLCHAINS_DIR / f"{name}.cmake"
    if dest.exists():
        Logger.warn(f"Toolchain {name} already exists")
        return
    if template == "custom-gnu":
        content = _generate_custom_gnu(name, prefix, cpu, fpu)
    elif template == "arm-none-eabi":
        content = "# arm-none-eabi toolchain stub\n"
    else:
        Logger.error(f"Unknown toolchain template: {template}")
        raise SystemExit(2)
    dest.write_text(content, encoding="utf-8")
    Logger.info(f"Wrote toolchain: {dest}")
    if gen_preset:
        # create a preset that sets CMAKE_TOOLCHAIN_FILE
        pname = f"{name}-preset"
        data = load_presets()
        cfgs = data.setdefault("configurePresets", [])
        if any(p.get("name") == pname for p in cfgs):
            Logger.warn(f"Preset {pname} already exists")
        else:
            cfgs.append({
                "name": pname,
                "generator": "Ninja",
                "binaryDir": f"build/{pname}",
                "toolchainFile": str(dest.as_posix()),
            })
            data.setdefault("buildPresets", []).append({"name": f"{pname}-build", "configurePreset": pname})
            save_presets(data)
            Logger.info(f"Generated preset {pname} referencing toolchain")


def _impl_cmd_toolchain_remove(args) -> None:
    name = getattr(args, "name")
    path = TOOLCHAINS_DIR / f"{name}.cmake"
    if not path.exists():
        Logger.warn(f"Toolchain {name} not found")
        return
    path.unlink()
    Logger.info(f"Removed toolchain {name}")


def _generate_custom_gnu(name: str, prefix: str, cpu: str, fpu: str) -> str:
    return (
        f"# Custom GNU toolchain generated for {name}\n"
        f"set(CMAKE_SYSTEM_NAME Linux)\n"
        f"set(CMAKE_C_COMPILER {prefix}gcc)\n"
        f"set(CMAKE_CXX_COMPILER {prefix}g++)\n"
    )


def _impl_cmd_config_get(args) -> None:
    key = getattr(args, "key", None)
    print(f"config get {key}: not implemented in this implementation")


def _impl_cmd_config_set(args) -> None:
    print("config set: not implemented in this implementation")


def _impl_cmd_test_run(args) -> None:
    target = getattr(args, "target", None)
    preset = getattr(args, "preset", None) or "gcc-debug-static-x86_64"
    if target:
        run_proc(["cmake", "--build", "--preset", preset, "--target", target + "_tests"])
    else:
        run_proc(["ctest", "--preset", preset, "--output-on-failure"])


def _impl_cmd_upgrade_std(args) -> None:
    print("upgrade-std: not implemented in this implementation")


def _impl_cmd_repo_list(args) -> None:
    # List git submodules and fetch deps
    gm = PROJECT_ROOT / ".gitmodules"
    if gm.exists():
        print("Git submodules (.gitmodules):")
        text = gm.read_text(encoding="utf-8")
        for m in re.finditer(r"\[submodule \"([^\"]+)\"\]", text):
            print(" -", m.group(1))
    if FETCH_DEPS_FILE.exists():
        print("Fetch deps:")
        for d in load_fetch_deps():
            print(f" - {d.get('name')} -> {d.get('url')} @ {d.get('tag')}")


def _impl_cmd_repo_add_submodule(args) -> None:
    url = getattr(args, "url")
    dest = getattr(args, "dest")
    branch = getattr(args, "branch", "main")
    dry = getattr(args, "dry_run", False)
    cmd = ["git", "submodule", "add", "-b", branch, url, dest]
    if dry:
        print("Dry-run:", " ".join(cmd))
        return
    run_proc(cmd, cwd=PROJECT_ROOT)
    Logger.info(f"Added submodule {url} -> {dest}")


def _impl_cmd_repo_add_fetch(args) -> None:
    name = getattr(args, "name")
    url = getattr(args, "url")
    tag = getattr(args, "tag", "main")
    dry = getattr(args, "dry_run", False)
    entry = {"name": name, "url": url, "tag": tag}
    if dry:
        print("Dry-run: would record fetch dep:", entry)
        return
    data = list(load_fetch_deps())
    data.append(entry)
    FETCH_DEPS_FILE.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    Logger.info(f"Recorded fetch dep: {name} -> {url}@{tag}")
    # Clear cached view after writing
    try:
        load_fetch_deps.cache_clear()
    except Exception:
        pass


def _impl_cmd_repo_sync(args) -> None:
    # Initialize and update git submodules, then fetch fetch-deps
    try:
        run_proc(["git", "submodule", "update", "--init", "--recursive"], cwd=PROJECT_ROOT)
    except SystemExit:
        Logger.warn("Submodule update failed")
    if FETCH_DEPS_FILE.exists():
        for d in load_fetch_deps():
            dest = PROJECT_ROOT / "external" / d.get("name")
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                # attempt pull
                try:
                    run_proc(["git", "-C", str(dest), "fetch"], cwd=PROJECT_ROOT)
                    run_proc(["git", "-C", str(dest), "checkout", d.get("tag")], cwd=PROJECT_ROOT)
                except SystemExit:
                    Logger.warn(f"Failed to update {d.get('name')}")
            else:
                try:
                    run_proc(["git", "clone", d.get("url"), str(dest)], cwd=PROJECT_ROOT)
                    run_proc(["git", "-C", str(dest), "checkout", d.get("tag")], cwd=PROJECT_ROOT)
                except SystemExit:
                    Logger.warn(f"Failed to clone {d.get('name')}")


def _impl_cmd_repo_versions(args) -> None:
    if not FETCH_DEPS_FILE.exists():
        print("No fetch deps recorded")
        return
    for d in load_fetch_deps():
        name = d.get("name")
        url = d.get("url")
        print(f"Versions for {name} ({url}):")
        try:
            out = subprocess.check_output(["git", "ls-remote", "--tags", url], stderr=subprocess.DEVNULL).decode()
            tags = [l.split('\t')[1] for l in out.splitlines() if '\trefs/tags/' in l]
            for t in tags[:10]:
                print(" -", t)
        except Exception:
            print("  (failed to list remote tags)")


def _impl_cmd_ci(args) -> None:
    print("ci simulation: running basic build+test")
    run_proc([sys.executable, str(PROJECT_ROOT / "scripts" / "tool.py"), "build", "check"])


def _impl_cmd_doctor(args) -> None:
    print("toolsolution doctor: running basic sanity checks")
    try:
        run_proc(["cmake", "--version"])
    except SystemExit:
        print("cmake missing or not working")
        raise
    try:
        run_proc([sys.executable, str(PROJECT_ROOT / "scripts" / "tool.py"), "lib", "doctor"])
    except SystemExit:
        print("lib doctor reported problems")
        raise
    print("toolsolution doctor: OK")


def _wrap(fn, args) -> CLIResult:
    try:
        fn(args)
        return CLIResult(success=True)
    except SystemExit as e:
        return CLIResult(success=(e.code == 0), code=e.code or 1)


def cmd_target_list(args):    return _wrap(_impl_cmd_target_list,    args)
def cmd_target_build(args):   return _wrap(_impl_cmd_target_build,   args)
def cmd_preset_list(args):    return _wrap(_impl_cmd_preset_list,    args)
def cmd_preset_add(args):     return _wrap(_impl_cmd_preset_add,     args)
def cmd_preset_remove(args):  return _wrap(_impl_cmd_preset_remove,  args)
def cmd_toolchain_list(args): return _wrap(_impl_cmd_toolchain_list, args)
def cmd_toolchain_add(args):  return _wrap(_impl_cmd_toolchain_add,  args)
def cmd_toolchain_remove(args): return _wrap(_impl_cmd_toolchain_remove, args)
def cmd_config_get(args):     return _wrap(_impl_cmd_config_get,     args)
def cmd_config_set(args):     return _wrap(_impl_cmd_config_set,     args)
def cmd_doctor(args):         return _wrap(_impl_cmd_doctor,         args)
def cmd_test_run(args):       return _wrap(_impl_cmd_test_run,       args)
def cmd_upgrade_std(args):    return _wrap(_impl_cmd_upgrade_std,    args)
def cmd_repo_list(args):      return _wrap(_impl_cmd_repo_list,      args)
def cmd_repo_add_submodule(args): return _wrap(_impl_cmd_repo_add_submodule, args)
def cmd_repo_add_fetch(args): return _wrap(_impl_cmd_repo_add_fetch, args)
def cmd_repo_sync(args):      return _wrap(_impl_cmd_repo_sync,      args)
def cmd_repo_versions(args):  return _wrap(_impl_cmd_repo_versions,  args)
def cmd_ci(args):             return _wrap(_impl_cmd_ci,             args)


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

    # doctor
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
