#!/usr/bin/env python3
"""
core/commands/sol.py — Project orchestration implementation.

Implements commands that used to live in `scripts/toolsolution.py`.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# ── Path bootstrap ────────────────────────────────────────────────────────────
_SCRIPTS = Path(__file__).resolve().parent.parent.parent  # scripts/
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from core.utils.common import (
    Logger,
    CLIResult,
    run_proc,
    run_capture,
    PROJECT_ROOT,
    json_read_cached,
    json_cache_clear,
    GlobalConfig,
)
import json
import re
from functools import lru_cache
try:
    from core.libpkg.jinja_helpers import render_template_file as _render_template_file
    _USE_JINJA_SOL = True
except Exception:
    _render_template_file = None
    _USE_JINJA_SOL = False

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
    for lib in libs:
        print(" -", lib)


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
    if _USE_JINJA_SOL:
        return _render_template_file("custom_gnu_toolchain.jinja2", name=name, prefix=prefix, cpu=cpu, fpu=fpu)

    return (
        f"# Custom GNU toolchain generated for {name}\n"
        f"set(CMAKE_SYSTEM_NAME Linux)\n"
        f"set(CMAKE_C_COMPILER {prefix}gcc)\n"
        f"set(CMAKE_CXX_COMPILER {prefix}g++)\n"
    )


def _impl_cmd_config_get(args) -> None:
    key = getattr(args, "key", None)
    if not key:
        # List all
        print(f"VERBOSE: {GlobalConfig.VERBOSE}")
        print(f"YES: {GlobalConfig.YES}")
        print(f"JSON: {GlobalConfig.JSON}")
        print(f"DRY_RUN: {GlobalConfig.DRY_RUN}")
        print(f"VERSION: {GlobalConfig.VERSION}")
        return
    
    key_upper = key.upper()
    if hasattr(GlobalConfig, key_upper):
        print(f"{key_upper}: {getattr(GlobalConfig, key_upper)}")
    else:
        print(f"Unknown config key: {key}")


def _impl_cmd_config_set(args) -> None:
    key = getattr(args, "key")
    value = getattr(args, "value")
    key_upper = key.upper()
    
    if not hasattr(GlobalConfig, key_upper):
        print(f"Unknown config key: {key}")
        return
    
    # Try to convert value to appropriate type
    current = getattr(GlobalConfig, key_upper)
    if isinstance(current, bool):
        new_val = value.lower() in ("true", "1", "yes", "on")
    elif isinstance(current, (int, float)):
        try:
            new_val = type(current)(value)
        except ValueError:
            print(f"Invalid value type for {key_upper}")
            return
    else:
        new_val = value
        
    setattr(GlobalConfig, key_upper, new_val)
    print(f"Set {key_upper} = {new_val} (Runtime only, persistent config not implemented yet)")


def _impl_cmd_test_run(args) -> None:
    target = getattr(args, "target", None)
    preset = getattr(args, "preset", None) or "gcc-debug-static-x86_64"
    if target:
        run_proc(["cmake", "--build", "--preset", preset, "--target", target + "_tests"])
    else:
        run_proc(["ctest", "--preset", preset, "--output-on-failure"])


def _impl_cmd_upgrade_std(args) -> None:
    std = getattr(args, "std")
    target = getattr(args, "target", None)
    dry = getattr(args, "dry_run", False)
    
    if target:
        # Upgrade only one library
        target_cm = PROJECT_ROOT / "libs" / target / "CMakeLists.txt"
        if not target_cm.exists():
            print(f"Library '{target}' not found")
            return
        files = [target_cm]
    else:
        # Upgrade project-wide (libs and apps)
        files = list(PROJECT_ROOT.rglob("CMakeLists.txt"))

    for cm in files:
        if cm.is_file():
            content = cm.read_text(encoding="utf-8")
            # Look for CXX_STANDARD
            new_content = re.sub(r'(CXX_STANDARD\s+)\d+', rf'\g<1>{std}', content)
            if new_content != content:
                if dry:
                    print(f"[dry-run] Would upgrade {cm.relative_to(PROJECT_ROOT)} to C++{std}")
                else:
                    cm.write_text(new_content, encoding="utf-8")
                    print(f"✅ Upgraded {cm.relative_to(PROJECT_ROOT)} to C++{std}")


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
            out, rc = run_capture(["git", "ls-remote", "--tags", url], cwd=PROJECT_ROOT)
            if rc == 0 and out:
                tags = [line.split('\t')[1] for line in out.splitlines() if '\trefs/tags/' in line]
                for t in tags[:10]:
                    print(" -", t)
        except Exception:
            print("  (failed to list remote tags)")


def _impl_cmd_ci(args) -> None:
    preset_filter = getattr(args, "preset_filter", "")
    fail_fast = getattr(args, "fail_fast", False)
    
    print(f"CI simulation: running build+test (filter: '{preset_filter}')")
    
    presets_data = load_presets()
    configs = presets_data.get("configurePresets", [])
    
    to_run = []
    for cfg in configs:
        name = cfg.get("name", "")
        if preset_filter in name:
            to_run.append(name)
            
    if not to_run:
        print(f"No presets match filter '{preset_filter}'")
        return

    for pname in to_run:
        print(f"\n--- Running CI for preset: {pname} ---")
        try:
            # Run build check for this preset
            run_proc([sys.executable, str(PROJECT_ROOT / "scripts" / "tool.py"), "build", "--preset", pname, "check", "--no-sync"])
        except SystemExit as e:
            if e.code != 0:
                print(f"❌ CI failed for preset: {pname}")
                if fail_fast:
                    raise
            continue
    print("\n✅ CI simulation finished")


def _impl_cmd_target_add(args) -> None:
    name = getattr(args, "name")
    dry = getattr(args, "dry_run", False)
    
    app_dir = PROJECT_ROOT / "apps" / name
    if app_dir.exists():
        print(f"App '{name}' already exists")
        return
        
    if dry:
        print(f"[dry-run] Would create apps/{name}/")
        print(f"[dry-run] Would register in apps/CMakeLists.txt")
        return
        
    from core.utils.fileops import Transaction
    with Transaction(PROJECT_ROOT) as txn:
        txn.safe_mkdir(app_dir / "src", parents=True, exist_ok=True)
        
        # Write CMakeLists.txt
        cm_content = (
            f"cmake_minimum_required(VERSION 3.25)\n"
            f"project({name} VERSION 1.0.0 LANGUAGES CXX)\n\n"
            f"add_executable({name} src/main.cpp)\n"
            f"target_link_libraries({name} PRIVATE dummy_lib)\n"
        )
        txn.safe_write_text(app_dir / "CMakeLists.txt", cm_content)
        
        # Write main.cpp
        cpp_content = (
            f"#include <iostream>\n"
            f"#include \"dummy_lib/greet.h\"\n\n"
            f"int main() {{\n"
            f"    std::cout << \"Hello from {name}!\" << std::endl;\n"
            f"    std::cout << \"Library says: \" << dummy_lib::get_greeting() << std::endl;\n"
            f"    return 0;\n"
            f"}}\n"
        )
        txn.safe_write_text(app_dir / "src" / "main.cpp", cpp_content)
        
        # Register in apps/CMakeLists.txt
        from core.libpkg.create import _cmake_add_subdirectory
        _cmake_add_subdirectory(PROJECT_ROOT / "apps" / "CMakeLists.txt", name)
        
    print(f"✅ Created apps/{name}/")


def _impl_cmd_check_extra(args) -> None:
    import shutil
    Logger.info("Running extra repository checks (ruff, mypy, cppcheck)...")
    
    overall_ok = True
    
    # 1. Ruff
    if shutil.which("ruff"):
        print("-- ruff (python linter) --")
        targets = ["scripts", "tests", "extension/src"]
        found = [t for t in targets if (PROJECT_ROOT / t).exists()]
        if found:
            rc = run_proc(["ruff", "check"] + found, check=False)
            if rc != 0: overall_ok = False
    else:
        Logger.warn("ruff not installed; skip. (pip install ruff)")

    # 2. Mypy
    if shutil.which("mypy"):
        print("\n-- mypy (type checks) --")
        rc = run_proc(["mypy", "scripts", "--ignore-missing-imports"], check=False)
        if rc != 0: overall_ok = False
    else:
        Logger.warn("mypy not installed; skip. (pip install mypy)")

    # 3. Cppcheck
    if shutil.which("cppcheck"):
        print("\n-- cppcheck (C++ static analysis) --")
        if (PROJECT_ROOT / "libs").exists():
            rc = run_proc(["cppcheck", "--enable=warning,style,portability", "--quiet", str(PROJECT_ROOT / "libs")], check=False)
            if rc != 0: overall_ok = False
    else:
        Logger.warn("cppcheck not installed; skip. (sudo apt install cppcheck)")

    if not overall_ok:
        Logger.error("One or more extra checks failed.")
        sys.exit(1)
    Logger.success("All installed extra checks passed.")


def _impl_cmd_init_skeleton(args) -> None:
    from core.utils.fileops import Transaction
    from core.utils.common import get_project_version, get_project_name
    try:
        from core.libpkg.jinja_helpers import render_template_file
    except ImportError:
        Logger.error("Jinja2 required for init-skeleton")
        return

    name = getattr(args, "name", None) or get_project_name()
    version = getattr(args, "version", None) or get_project_version()
    dry = getattr(args, "dry_run", False)

    Logger.info(f"Regenerating project skeleton for '{name}' v{version}...")

    # Root context
    ctx = {
        "project_name": name,
        "version": version,
        "description": "Professional Modern C++ / CMake Project Template",
        "author": "develooper1994",
        "contact": "https://github.com/develooper1994",
    }

    if dry:
        print("[dry-run] Would regenerate root CMakeLists.txt and subdir CMakeLists.txt")
        return

    with Transaction(PROJECT_ROOT) as txn:
        # 1. Root CMakeLists.txt
        txn.safe_write_text(PROJECT_ROOT / "CMakeLists.txt", render_template_file("root_cmakelists.jinja2", **ctx))

        # 2. Subdir CMakeLists.txt
        for dname in ["libs", "apps", "tests/unit"]:
            dpath = PROJECT_ROOT / dname
            if not dpath.exists():
                txn.safe_mkdir(dpath, parents=True)
            
            subs = sorted([p.name for p in dpath.iterdir() if p.is_dir() and (p / "CMakeLists.txt").exists()])
            content = render_template_file("subdir_cmakelists.jinja2", dir_name=dname, subdirectories=subs)
            txn.safe_write_text(dpath / "CMakeLists.txt", content)

    Logger.success("Project skeleton regenerated.")


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


def cmd_target_list(args):
    return _wrap(_impl_cmd_target_list, args)


def cmd_target_build(args):
    return _wrap(_impl_cmd_target_build, args)


def cmd_target_add(args):
    return _wrap(_impl_cmd_target_add, args)


def cmd_preset_list(args):
    return _wrap(_impl_cmd_preset_list, args)


def cmd_preset_add(args):
    return _wrap(_impl_cmd_preset_add, args)


def cmd_preset_remove(args):
    return _wrap(_impl_cmd_preset_remove, args)


def cmd_toolchain_list(args):
    return _wrap(_impl_cmd_toolchain_list, args)


def cmd_toolchain_add(args):
    return _wrap(_impl_cmd_toolchain_add, args)


def cmd_toolchain_remove(args):
    return _wrap(_impl_cmd_toolchain_remove, args)


def cmd_config_get(args):
    return _wrap(_impl_cmd_config_get, args)


def cmd_config_set(args):
    return _wrap(_impl_cmd_config_set, args)


def cmd_doctor(args):
    return _wrap(_impl_cmd_doctor, args)


def cmd_test_run(args):
    return _wrap(_impl_cmd_test_run, args)


def cmd_upgrade_std(args):
    return _wrap(_impl_cmd_upgrade_std, args)


def cmd_repo_list(args):
    return _wrap(_impl_cmd_repo_list, args)


def cmd_repo_add_submodule(args):
    return _wrap(_impl_cmd_repo_add_submodule, args)


def cmd_repo_add_fetch(args):
    return _wrap(_impl_cmd_repo_add_fetch, args)


def cmd_repo_sync(args):
    return _wrap(_impl_cmd_repo_sync, args)


def cmd_repo_versions(args):
    return _wrap(_impl_cmd_repo_versions, args)


def cmd_check_extra(args):
    return _wrap(_impl_cmd_check_extra, args)


def cmd_init_skeleton(args):
    return _wrap(_impl_cmd_init_skeleton, args)


def cmd_ci(args):
    return _wrap(_impl_cmd_ci, args)


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
