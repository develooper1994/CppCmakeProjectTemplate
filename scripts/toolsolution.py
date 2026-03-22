#!/usr/bin/env python3
"""
toolsolution.py — Full project orchestrator.

Manages targets, presets, toolchains, build config and project-wide operations.

Commands:
    target   list                            List all libs and apps
    target   build <n> [--preset X]         Build a single target
    target   add-app <n>                     Scaffold a new app (stub)

    preset   list                            List available presets
    preset   add  --compiler gcc --type debug --link static --arch x86_64
                  [--name override]          Add a new configure+build preset
    preset   remove <n>                      Remove a preset pair

    toolchain list                           List registered toolchains
    toolchain add --name <n> --template <t>  Add toolchain from template
              --prefix /path/to/bin/prefix-  (for custom-gnu)
              --cpu <cpu> --fpu <fpu>        (for arm)
              [--gen-preset]                 Also generate a CMakePresets entry
    toolchain remove <n>                     Remove toolchain + its presets

    config   get [key]                       Show project config summary
    config   set <key> <value>               Set a CMake option in base preset

    doctor                                   Full project health check
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (
    PROJECT_ROOT, default_preset, get_project_name, get_project_version,
    list_all_targets, list_presets, run, header, fail,
)

TOOLCHAINS_DIR  = PROJECT_ROOT / "cmake" / "toolchains"
PRESETS_FILE    = PROJECT_ROOT / "CMakePresets.json"

# ──────────────────────────────────────────────────────────────────────────────
# Preset JSON helpers
# ──────────────────────────────────────────────────────────────────────────────

def load_presets() -> dict:
    return json.loads(PRESETS_FILE.read_text(encoding="utf-8"))


def save_presets(data: dict) -> None:
    PRESETS_FILE.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


# ──────────────────────────────────────────────────────────────────────────────
# target
# ──────────────────────────────────────────────────────────────────────────────

def cmd_target_list(_: argparse.Namespace) -> None:
    targets = list_all_targets()
    print(f"Project: {get_project_name()} v{get_project_version()}")
    print(f"\nLibraries ({len(targets['libs'])}):")
    for n in targets["libs"]:
        print(f"  lib  {n}")
    print(f"\nApplications ({len(targets['apps'])}):")
    for n in targets["apps"]:
        print(f"  app  {n}")


def cmd_target_build(args: argparse.Namespace) -> None:
    preset  = args.preset or default_preset()
    target  = args.name
    header(f"Build target: {target}", f"Preset: {preset}")

    build_dir = PROJECT_ROOT / "build" / preset

    # Configure if build dir doesn't exist
    if not build_dir.exists():
        print("\n[1/2] Configure...")
        run(["cmake", "--preset", preset])

    print("\n[2/2] Build target...")
    run(["cmake", "--build", str(build_dir), "--target", target])
    print(f"\n✅ {target} built.")


# ──────────────────────────────────────────────────────────────────────────────
# preset
# ──────────────────────────────────────────────────────────────────────────────

VALID_COMPILERS = {"gcc", "clang", "msvc"}
VALID_TYPES     = {"debug", "release", "relwithdebinfo"}
VALID_LINKS     = {"static", "dynamic"}
VALID_ARCHES    = {"x86_64", "x86", "x64", "win32"}

# Map to CMake values
_BUILD_TYPE = {
    "debug":          "Debug",
    "release":        "Release",
    "relwithdebinfo": "RelWithDebInfo",
}
_SHARED = {"static": "OFF", "dynamic": "ON"}
_MSVC_ARCH = {"x86_64": "x64", "x64": "x64", "x86": "win32", "win32": "win32"}


def _make_preset_name(compiler: str, btype: str, link: str, arch: str) -> str:
    return f"{compiler}-{btype}-{link}-{arch}"


def cmd_preset_list(_: argparse.Namespace) -> None:
    names = list_presets()
    print(f"Available presets ({len(names)}):")
    for n in names:
        print(f"  {n}")


def cmd_preset_add(args: argparse.Namespace) -> None:
    compiler = args.compiler.lower()
    btype    = args.type.lower()
    link     = args.link.lower()
    arch     = args.arch.lower()

    if compiler not in VALID_COMPILERS:
        fail(f"Unknown compiler '{compiler}'. Choose: {', '.join(VALID_COMPILERS)}")
    if btype not in VALID_TYPES:
        fail(f"Unknown type '{btype}'. Choose: {', '.join(VALID_TYPES)}")
    if link not in VALID_LINKS:
        fail(f"Unknown link '{link}'. Choose: {', '.join(VALID_LINKS)}")

    name = args.name or _make_preset_name(compiler, btype, link, arch)
    data = load_presets()

    existing = [p["name"] for p in data.get("configurePresets", [])]
    if name in existing:
        fail(f"Preset '{name}' already exists.")

    is_msvc   = compiler == "msvc"
    is_linux  = not is_msvc
    is_x86    = arch in ("x86", "win32")

    # Determine base preset
    if is_msvc:
        base = "win-base"
    elif compiler == "gcc":
        base = "linux-gcc-base"
    else:
        base = "linux-clang-base"

    cache_vars: dict = {
        "CMAKE_BUILD_TYPE": _BUILD_TYPE[btype],
        "BUILD_SHARED_LIBS": _SHARED[link],
    }

    config_preset: dict = {
        "name":     name,
        "inherits": base,
        "cacheVariables": cache_vars,
    }

    if is_msvc:
        config_preset["architecture"] = _MSVC_ARCH.get(arch, "x64")
    elif is_x86:
        cache_vars.update({
            "CMAKE_CXX_FLAGS":         "-m32",
            "CMAKE_C_FLAGS":           "-m32",
            "CMAKE_EXE_LINKER_FLAGS":  "-m32",
            "CMAKE_SHARED_LINKER_FLAGS": "-m32",
        })

    data.setdefault("configurePresets", []).append(config_preset)
    data.setdefault("buildPresets", []).append(
        {"name": name, "configurePreset": name}
    )
    save_presets(data)
    print(f"  ✅ Preset added: {name}")


def cmd_preset_remove(args: argparse.Namespace) -> None:
    name = args.name
    data = load_presets()

    before_cfg   = len(data.get("configurePresets", []))
    before_build = len(data.get("buildPresets", []))

    data["configurePresets"] = [
        p for p in data.get("configurePresets", []) if p["name"] != name
    ]
    data["buildPresets"] = [
        p for p in data.get("buildPresets", []) if p["name"] != name
    ]
    data["testPresets"] = [
        p for p in data.get("testPresets", []) if p.get("name") != name and p.get("configurePreset") != name
    ]

    if len(data["configurePresets"]) == before_cfg:
        fail(f"Preset '{name}' not found.")

    save_presets(data)
    print(f"  ✅ Preset removed: {name}")


# ──────────────────────────────────────────────────────────────────────────────
# toolchain
# ──────────────────────────────────────────────────────────────────────────────

TOOLCHAIN_TEMPLATES = ["custom-gnu", "arm-none-eabi"]


def cmd_toolchain_list(_: argparse.Namespace) -> None:
    files = sorted(TOOLCHAINS_DIR.glob("*.cmake"))
    print(f"Toolchains ({len(files)}):")
    for f in files:
        print(f"  {f.stem}  ({f.name})")
    print(f"\nTemplates available: {', '.join(TOOLCHAIN_TEMPLATES)}")


def _generate_custom_gnu(name: str, prefix: str, cpu: str, fpu: str) -> str:
    return f"""\
# cmake/toolchains/{name}.cmake
# Generated by toolsolution.py — customize as needed.

set(CMAKE_SYSTEM_NAME      Generic)
set(CMAKE_SYSTEM_PROCESSOR {cpu or "unknown"})

set(TOOLCHAIN_PREFIX "{prefix}")
set(CMAKE_C_COMPILER   "${{TOOLCHAIN_PREFIX}}gcc")
set(CMAKE_CXX_COMPILER "${{TOOLCHAIN_PREFIX}}g++")
set(CMAKE_ASM_COMPILER "${{TOOLCHAIN_PREFIX}}gcc")
set(CMAKE_OBJCOPY      "${{TOOLCHAIN_PREFIX}}objcopy" CACHE INTERNAL "")
set(CMAKE_SIZE         "${{TOOLCHAIN_PREFIX}}size"    CACHE INTERNAL "")

{"set(MCU_FLAGS " + chr(34) + f"-mcpu={cpu}" + (f" -mfpu={fpu} -mfloat-abi=hard" if fpu else "") + chr(34) + ")" if cpu else ""}
set(CMAKE_C_FLAGS   "${{MCU_FLAGS}} -ffunction-sections -fdata-sections" CACHE STRING "")
set(CMAKE_CXX_FLAGS "${{MCU_FLAGS}} -ffunction-sections -fdata-sections" CACHE STRING "")
# set(CMAKE_EXE_LINKER_FLAGS "--specs=nosys.specs -Wl,--gc-sections -T linker.ld" CACHE STRING "")

set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)
"""


def cmd_toolchain_add(args: argparse.Namespace) -> None:
    name     = args.name
    template = args.template.lower()
    prefix   = getattr(args, "prefix",  "") or ""
    cpu      = getattr(args, "cpu",     "") or ""
    fpu      = getattr(args, "fpu",     "") or ""

    if template not in TOOLCHAIN_TEMPLATES:
        fail(f"Unknown template '{template}'. Available: {', '.join(TOOLCHAIN_TEMPLATES)}")

    tc_file = TOOLCHAINS_DIR / f"{name}.cmake"
    if tc_file.exists():
        fail(f"Toolchain '{name}.cmake' already exists.")

    if template == "custom-gnu":
        if not prefix:
            fail("--prefix is required for custom-gnu template (e.g. /opt/sdk/bin/arm-none-eabi-)")
        content = _generate_custom_gnu(name, prefix, cpu, fpu)
    elif template == "arm-none-eabi":
        # Copy and patch the existing arm template
        src = TOOLCHAINS_DIR / "arm-none-eabi.cmake"
        content = src.read_text(encoding="utf-8")
        if cpu:
            content = re.sub(r'-mcpu=\S+', f'-mcpu={cpu}', content)
        if fpu:
            content = re.sub(r'-mfpu=\S+', f'-mfpu={fpu}', content)
        content = f"# cmake/toolchains/{name}.cmake\n# Derived from arm-none-eabi.cmake\n" + content

    tc_file.write_text(content, encoding="utf-8")
    print(f"  ✅ Toolchain created: cmake/toolchains/{name}.cmake")

    if getattr(args, "gen_preset", False):
        preset_name = f"embedded-{name}"
        data = load_presets()
        existing = [p["name"] for p in data.get("configurePresets", [])]
        if preset_name in existing:
            print(f"  ⏭  Preset '{preset_name}' already exists, skipped.")
        else:
            data.setdefault("configurePresets", []).append({
                "name":          preset_name,
                "displayName":   f"Embedded: {name}",
                "inherits":      "base",
                "generator":     "Ninja",
                "toolchainFile": f"${{sourceDir}}/cmake/toolchains/{name}.cmake",
                "cacheVariables": {
                    "CMAKE_BUILD_TYPE": "Release",
                    "ENABLE_UNIT_TESTS": "OFF",
                },
            })
            data.setdefault("buildPresets", []).append(
                {"name": preset_name, "configurePreset": preset_name}
            )
            save_presets(data)
            print(f"  ✅ Preset generated: {preset_name}")


def cmd_toolchain_remove(args: argparse.Namespace) -> None:
    name    = args.name
    tc_file = TOOLCHAINS_DIR / f"{name}.cmake"

    if not tc_file.exists():
        fail(f"Toolchain '{name}.cmake' not found.")

    tc_file.unlink()
    print(f"  ✅ Toolchain deleted: cmake/toolchains/{name}.cmake")

    # Remove related presets
    data = load_presets()
    tc_rel = f"cmake/toolchains/{name}.cmake"
    before = len(data.get("configurePresets", []))

    data["configurePresets"] = [
        p for p in data.get("configurePresets", [])
        if tc_rel not in p.get("toolchainFile", "")
    ]
    removed_names = {
        p["name"] for p in data.get("buildPresets", [])
        if not any(
            cp["name"] == p.get("configurePreset")
            for cp in data["configurePresets"]
        )
    }
    data["buildPresets"] = [
        p for p in data.get("buildPresets", [])
        if p["name"] not in removed_names
    ]

    if len(data["configurePresets"]) < before:
        save_presets(data)
        print(f"  ✅ Associated presets removed.")


# ──────────────────────────────────────────────────────────────────────────────
# config
# ──────────────────────────────────────────────────────────────────────────────

def cmd_config_get(args: argparse.Namespace) -> None:
    data = load_presets()
    base = next((p for p in data.get("configurePresets", []) if p["name"] == "base"), {})
    cache = base.get("cacheVariables", {})

    print(f"Project : {get_project_name()} v{get_project_version()}")
    print(f"Root    : {PROJECT_ROOT}")
    print(f"\nBase preset cache variables:")
    if args.key:
        val = cache.get(args.key, "<not set>")
        print(f"  {args.key} = {val}")
    else:
        for k, v in cache.items():
            print(f"  {k} = {v}")


def cmd_config_set(args: argparse.Namespace) -> None:
    data  = load_presets()
    base  = next((p for p in data["configurePresets"] if p["name"] == "base"), None)
    if not base:
        fail("'base' preset not found in CMakePresets.json")

    base.setdefault("cacheVariables", {})[args.key] = args.value
    save_presets(data)
    print(f"  ✅ base preset: {args.key} = {args.value}")


# ──────────────────────────────────────────────────────────────────────────────
# doctor
# ──────────────────────────────────────────────────────────────────────────────

def cmd_doctor(_: argparse.Namespace) -> None:
    issues = 0

    # 1. toollib doctor
    toollib = PROJECT_ROOT / "scripts" / "toollib.py"
    if toollib.exists():
        ret = subprocess.run(
            [sys.executable, str(toollib), "doctor"],
            cwd=PROJECT_ROOT,
        ).returncode
        if ret != 0:
            issues += 1
    else:
        print("  ⚠  toollib.py not found — skipping lib checks")
        issues += 1

    # 2. Preset JSON validity
    try:
        json.loads(PRESETS_FILE.read_text(encoding="utf-8"))
        print("  ✅ CMakePresets.json valid")
    except json.JSONDecodeError as e:
        print(f"  ❌ CMakePresets.json invalid: {e}")
        issues += 1

    # 3. Orphan buildPresets
    data = load_presets()
    cfg_names = {p["name"] for p in data.get("configurePresets", [])}
    for bp in data.get("buildPresets", []):
        if bp.get("configurePreset") not in cfg_names:
            print(f"  ⚠  Orphan buildPreset: {bp['name']} → {bp.get('configurePreset')}")
            issues += 1

    # 4. Toolchain files referenced by presets exist
    for p in data.get("configurePresets", []):
        tc = p.get("toolchainFile", "")
        if tc:
            tc_path = PROJECT_ROOT / tc.replace("${sourceDir}/", "")
            if not tc_path.exists():
                print(f"  ⚠  Missing toolchain: {tc} (preset: {p['name']})")
                issues += 1

    if issues == 0:
        print("  ✅ Solution healthy")
    else:
        print(f"\n  {issues} issue(s) found.")
        raise SystemExit(1)


# ──────────────────────────────────────────────────────────────────────────────
# repo management
# ──────────────────────────────────────────────────────────────────────────────

_GITMODULES = PROJECT_ROOT / ".gitmodules"


def _read_gitmodules() -> list[dict]:
    """Parse .gitmodules into a list of {name, path, url} dicts."""
    if not _GITMODULES.exists():
        return []
    import configparser as _cp
    cfg = _cp.ConfigParser()
    cfg.read(str(_GITMODULES), encoding="utf-8")
    result = []
    for section in cfg.sections():
        if section.startswith("submodule "):
            name = section.split('"')[1]
            result.append({
                "name": name,
                "path": cfg.get(section, "path", fallback=""),
                "url":  cfg.get(section, "url",  fallback=""),
            })
    return result


def _read_fetch_deps() -> list[dict]:
    """Parse external/fetch_deps.cmake for FetchContent_Declare blocks."""
    fetch_cmake = PROJECT_ROOT / "external" / "fetch_deps.cmake"
    if not fetch_cmake.exists():
        return []
    import re as _re
    content = fetch_cmake.read_text(encoding="utf-8")
    result = []
    for m in _re.finditer(
        r'FetchContent_Declare\((\w+)\s+GIT_REPOSITORY\s+(\S+)\s+GIT_TAG\s+(\S+)',
        content,
    ):
        result.append({"name": m.group(1), "url": m.group(2), "tag": m.group(3)})
    return result


def cmd_repo_list(_: argparse.Namespace) -> None:
    submodules   = _read_gitmodules()
    fetch_deps   = _read_fetch_deps()

    print(f"\nSubmodules ({len(submodules)}):")
    for s in submodules:
        print(f"  {s['path']:<30} {s['url']}")
    if not submodules:
        print("  (none)")

    print(f"\nFetchContent deps ({len(fetch_deps)}):")
    for f in fetch_deps:
        print(f"  {f['name']:<20} {f['url']}  @ {f['tag']}")
    if not fetch_deps:
        print("  (none)")


def cmd_repo_add_submodule(args: argparse.Namespace) -> None:
    dest   = args.dest   # e.g. libs/core
    url    = args.url
    branch = args.branch

    if args.dry_run:
        print(f"[dry-run] git submodule add -b {branch} {url} {dest}")
        return

    dest_path = PROJECT_ROOT / dest
    if dest_path.exists() and any(dest_path.iterdir()):
        fail(f"Destination '{dest}' already exists and is non-empty")

    print(f"  Adding submodule {url} → {dest}...")
    r = subprocess.run(
        ["git", "submodule", "add", "-b", branch, url, dest],
        cwd=PROJECT_ROOT,
    )
    if r.returncode != 0:
        fail("git submodule add failed")

    # Register in libs/CMakeLists.txt if dest starts with libs/
    if dest.startswith("libs/"):
        lib_name = dest.split("/")[-1]
        libs_cmake = PROJECT_ROOT / "libs" / "CMakeLists.txt"
        content = libs_cmake.read_text(encoding="utf-8")
        if f"add_subdirectory({lib_name})" not in content:
            libs_cmake.write_text(
                content.rstrip() + f"\nadd_subdirectory({lib_name})\n",
                encoding="utf-8",
            )
            print(f"  ✅ libs/CMakeLists.txt: add_subdirectory({lib_name}) added")
    print(f"  ✅ Submodule added: {dest}")
    print(f"  ℹ  Run: git submodule update --init --recursive")


def cmd_repo_add_fetch(args: argparse.Namespace) -> None:
    """Register a top-level FetchContent dep (not linked to any lib)."""
    fetch_cmake = PROJECT_ROOT / "external" / "fetch_deps.cmake"
    root_cmake  = PROJECT_ROOT / "CMakeLists.txt"

    if args.dry_run:
        print(f"[dry-run] external/fetch_deps.cmake: FetchContent_Declare({args.name} @ {args.tag})")
        return

    fetch_cmake.parent.mkdir(exist_ok=True)
    if fetch_cmake.exists():
        existing = fetch_cmake.read_text(encoding="utf-8")
    else:
        existing = (
            "# external/fetch_deps.cmake\n"
            "# Managed by: toolsolution.py / toollib.py\n"
            "include(FetchContent)\n\n"
        )

    if args.name in existing:
        print(f"  ⏭  {args.name} already in fetch_deps.cmake")
    else:
        block = (
            f"# ── {args.name} ────────────────────────────────\n"
            f"FetchContent_Declare({args.name}\n"
            f"    GIT_REPOSITORY {args.url}\n"
            f"    GIT_TAG        {args.tag}\n"
            f"    SYSTEM\n)\n"
            f"FetchContent_MakeAvailable({args.name})\n"
        )
        fetch_cmake.write_text(existing + "\n" + block, encoding="utf-8")
        print(f"  ✅ external/fetch_deps.cmake: {args.name} added")

    # Hook into root CMakeLists if not already done
    root_content = root_cmake.read_text(encoding="utf-8")
    if "fetch_deps" not in root_content:
        import re as _re
        m = _re.search(r'^add_subdirectory\(libs\)', root_content, _re.MULTILINE)
        if m:
            include_line = 'include("${CMAKE_CURRENT_SOURCE_DIR}/external/fetch_deps.cmake" OPTIONAL)'
            insert = f"\n# External FetchContent dependencies\n{include_line}\n\n"
            root_content = root_content[:m.start()] + insert + root_content[m.start():]
            root_cmake.write_text(root_content, encoding="utf-8")
            print(f"  ✅ CMakeLists.txt: include(external/fetch_deps.cmake) added")


def cmd_repo_sync(_: argparse.Namespace) -> None:
    print("  Updating all submodules...")
    r = subprocess.run(
        ["git", "submodule", "update", "--remote", "--merge"],
        cwd=PROJECT_ROOT,
    )
    if r.returncode == 0:
        print("  ✅ Submodules updated")
    else:
        fail("git submodule update failed")


def cmd_repo_versions(_: argparse.Namespace) -> None:
    print(f"\n  {'Component':<30} {'Version/Tag':<20} {'Source'}")
    print(f"  {'-'*30} {'-'*20} {'-'*20}")

    # 1. Solution version
    v = get_project_version()
    n = get_project_name()
    print(f"  {n:<30} {v:<20} CMakeLists.txt")

    # 2. Submodule versions (last tag in each)
    for s in _read_gitmodules():
        sub_path = PROJECT_ROOT / s["path"]
        if sub_path.exists():
            try:
                tag = subprocess.check_output(
                    ["git", "describe", "--tags", "--abbrev=0"],
                    cwd=sub_path, stderr=subprocess.DEVNULL,
                ).decode().strip()
            except Exception:
                tag = "(no tag)"
        else:
            tag = "(not initialized)"
        print(f"  {s['path']:<30} {tag:<20} submodule")

    # 3. FetchContent deps
    for f in _read_fetch_deps():
        print(f"  {f['name']:<30} {f['tag']:<20} FetchContent")


# ──────────────────────────────────────────────────────────────────────────────
# test / upgrade-std
# ──────────────────────────────────────────────────────────────────────────────

def cmd_test_run(args: argparse.Namespace) -> None:
    """Run tests for all libraries or a single target."""
    preset = args.preset or default_preset()
    build_dir = PROJECT_ROOT / "build" / preset

    if not build_dir.exists():
        print(f"  Configuring '{preset}'...")
        run(["cmake", "--preset", preset])

    if args.target:
        # Build and run a single test binary
        test_bin = build_dir / "tests" / "unit" / args.target / f"{args.target}_tests"
        run(["cmake", "--build", str(build_dir), "--target", f"{args.target}_tests"])
        if test_bin.exists():
            run([str(test_bin)])
        else:
            fail(f"Test binary not found: {test_bin}")
    else:
        run(["cmake", "--build", str(build_dir)])
        run(["ctest", "--preset", preset, "--output-on-failure"])


def cmd_upgrade_std(args: argparse.Namespace) -> None:
    """Update C++ standard solution-wide or for a specific library."""
    std = args.std

    if args.target:
        # Per-library: update <LIB>_CXX_STANDARD cache var in its CMakeLists.txt
        lib_cmake = PROJECT_ROOT / "libs" / args.target / "CMakeLists.txt"
        if not lib_cmake.exists():
            fail(f"libs/{args.target}/CMakeLists.txt not found")
        content = lib_cmake.read_text(encoding="utf-8")
        varname = f"{args.target.upper()}_CXX_STANDARD"
        import re as _re
        new_content = _re.sub(
            rf'({re.escape(varname)}\s+")([^"]*)(")',
            rf'\g<1>{std}\3',
            content,
        )
        if new_content == content:
            print(f"  ⚠  {varname} pattern not found — add --cxx-standard when creating the lib")
        elif not args.dry_run:
            lib_cmake.write_text(new_content, encoding="utf-8")
            print(f"  ✅ {args.target}: CXX_STANDARD → C++{std}")
        else:
            print(f"[dry-run] {args.target}: CXX_STANDARD → C++{std}")
    else:
        # Solution-wide: update CMAKE_CXX_STANDARD in base preset
        data = load_presets()
        base = next((p for p in data["configurePresets"] if p["name"] == "base"), None)
        if not base:
            fail("'base' preset not found")
        if args.dry_run:
            print(f"[dry-run] base preset: CMAKE_CXX_STANDARD → {std}")
            return
        base.setdefault("cacheVariables", {})["CMAKE_CXX_STANDARD"] = std
        save_presets(data)
        print(f"  ✅ Solution-wide: CMAKE_CXX_STANDARD → {std}")
        print(f"  ⚠  Re-run cmake configure to apply.")


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="toolsolution.py",
        description="Full project orchestrator — targets, presets, toolchains, config",
    )
    sub = parser.add_subparsers(dest="group", required=True)
    # Lib delegation
    p = sub.add_parser("lib", help="Delegate to toollib.py")
    p.add_argument("args", nargs=argparse.REMAINDER)
    p.set_defaults(func=cmd_lib_delegate)
    
    # CI pipeline
    p = sub.add_parser("ci", help="Run CI")
    p.add_argument("--preset-filter", default=None)
    p.add_argument("--fail-fast", action="store_true")
    p.set_defaults(func=cmd_ci)


    # ── target ──────────────────────────────────────────────────────────────
    tgt = sub.add_parser("target", help="Manage build targets")
    tgt_sub = tgt.add_subparsers(dest="action", required=True)

    tgt_sub.add_parser("list", help="List all targets").set_defaults(func=cmd_target_list)

    p = tgt_sub.add_parser("build", help="Build a single target")
    p.add_argument("name",     help="CMake target name")
    p.add_argument("--preset", default=None)
    p.set_defaults(func=cmd_target_build)

    # ── preset ──────────────────────────────────────────────────────────────
    pre = sub.add_parser("preset", help="Manage CMake presets")
    pre_sub = pre.add_subparsers(dest="action", required=True)

    pre_sub.add_parser("list", help="List presets").set_defaults(func=cmd_preset_list)

    p = pre_sub.add_parser("add", help="Add a new preset")
    p.add_argument("--compiler", required=True, choices=list(VALID_COMPILERS))
    p.add_argument("--type",     required=True, choices=list(VALID_TYPES))
    p.add_argument("--link",     required=True, choices=list(VALID_LINKS))
    p.add_argument("--arch",     default="x86_64")
    p.add_argument("--name",     default=None,  help="Override auto-generated name")
    p.set_defaults(func=cmd_preset_add)

    p = pre_sub.add_parser("remove", help="Remove a preset")
    p.add_argument("name")
    p.set_defaults(func=cmd_preset_remove)

    # ── toolchain ────────────────────────────────────────────────────────────
    tc = sub.add_parser("toolchain", help="Manage toolchains")
    tc_sub = tc.add_subparsers(dest="action", required=True)

    tc_sub.add_parser("list", help="List toolchains").set_defaults(func=cmd_toolchain_list)

    p = tc_sub.add_parser("add", help="Add a toolchain from template")
    p.add_argument("--name",       required=True, help="New toolchain name (no extension)")
    p.add_argument("--template",   required=True, choices=TOOLCHAIN_TEMPLATES)
    p.add_argument("--prefix",     default="",    help="Compiler prefix path")
    p.add_argument("--cpu",        default="",    help="CPU (e.g. cortex-m4)")
    p.add_argument("--fpu",        default="",    help="FPU (e.g. fpv4-sp-d16)")
    p.add_argument("--gen-preset", action="store_true", help="Auto-generate a CMakePresets entry")
    p.set_defaults(func=cmd_toolchain_add)

    p = tc_sub.add_parser("remove", help="Remove a toolchain + its presets")
    p.add_argument("name")
    p.set_defaults(func=cmd_toolchain_remove)

    # ── config ───────────────────────────────────────────────────────────────
    cfg = sub.add_parser("config", help="Project-wide config")
    cfg_sub = cfg.add_subparsers(dest="action", required=True)

    p = cfg_sub.add_parser("get", help="Get config value(s)")
    p.add_argument("key", nargs="?", default=None)
    p.set_defaults(func=cmd_config_get)

    p = cfg_sub.add_parser("set", help="Set a base-preset cache variable")
    p.add_argument("key")
    p.add_argument("value")
    p.set_defaults(func=cmd_config_set)

    # ── test ─────────────────────────────────────────────────────────────────
    p = sub.add_parser("test", help="Run tests (all or single target)")
    p.add_argument("target", nargs="?", default=None, help="Library name (omit = all)")
    p.add_argument("--preset", default=None)
    p.set_defaults(func=cmd_test_run)

    # ── upgrade-std ──────────────────────────────────────────────────────────
    p = sub.add_parser("upgrade-std", help="Set C++ standard solution-wide or per-lib")
    p.add_argument("--std",    required=True, choices=["14", "17", "20", "23"])
    p.add_argument("--target", default=None,  help="Specific lib (omit = solution-wide)")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_upgrade_std)

    # ── repo ───────────────────────────────────────────────────────────────
    repo = sub.add_parser("repo", help="Multi-repo management (submodules, FetchContent)")
    repo_sub = repo.add_subparsers(dest="action", required=True)

    p = repo_sub.add_parser("add-submodule", help="Add a git submodule as a library")
    p.add_argument("--url",   required=True, help="Git remote URL")
    p.add_argument("--dest",  required=True, help="Destination path (e.g. libs/core)")
    p.add_argument("--branch", default="main")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_repo_add_submodule)

    p = repo_sub.add_parser("add-fetch", help="Register a FetchContent external dependency")
    p.add_argument("--name",   required=True, help="CMake FetchContent name")
    p.add_argument("--url",    required=True, help="Git remote URL")
    p.add_argument("--tag",    default="main", help="Git tag / commit hash")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_repo_add_fetch)

    repo_sub.add_parser("sync",     help="Update all submodules to latest"
                        ).set_defaults(func=cmd_repo_sync)
    repo_sub.add_parser("versions", help="Show version of each component"
                        ).set_defaults(func=cmd_repo_versions)
    repo_sub.add_parser("list",     help="List submodules and FetchContent deps"
                        ).set_defaults(func=cmd_repo_list)

    # ── doctor ───────────────────────────────────────────────────────────────
    sub.add_parser("doctor", help="Full project health check").set_defaults(func=cmd_doctor)

    return parser


def main() -> None:
    # Special case: toolsolution --lib <toollib args...>
    # Routes everything after --lib directly to toollib.py
    if "--lib" in sys.argv:
        idx = sys.argv.index("--lib")
        lib_args = sys.argv[idx + 1:]
        toollib = Path(__file__).resolve().parent / "toollib.py"
        if not toollib.exists():
            fail("toollib.py not found")
        result = subprocess.run([sys.executable, str(toollib)] + lib_args)
        sys.exit(result.returncode)

    args = build_parser().parse_args()
    args.func(args)


def cmd_lib_delegate(args: argparse.Namespace) -> None:
    cmd = [sys.executable, str(Path(__file__).resolve().parent / "toollib.py")] + args.args
    subprocess.run(cmd)

def cmd_ci(args: argparse.Namespace) -> None:
    all_presets = list_presets()
    target = [p for p in all_presets if not args.preset_filter or args.preset_filter in p]
    if not target: fail("No matching presets.")
    header("CI Pipeline", f"Presets: {len(target)}")
    for p in target:
        print(f"\n[CI] Running: {p}")
        run(["cmake", "--preset", p])
        run(["cmake", "--build", "--preset", p])
        ctest_bin = PROJECT_ROOT / "build" / p
        res = subprocess.run(["ctest", "--test-dir", str(ctest_bin), "--output-on-failure"])
        if res.returncode != 0:
            if args.fail_fast: fail(f"CI failed on {p}")
            print(f"  ❌ {p} FAILED")
        else:
            print(f"  ✅ {p} PASSED")

if __name__ == "__main__":
    main()
