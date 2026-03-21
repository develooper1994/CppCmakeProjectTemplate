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
# CLI
# ──────────────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="toolsolution.py",
        description="Full project orchestrator — targets, presets, toolchains, config",
    )
    sub = parser.add_subparsers(dest="group", required=True)

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

    # ── doctor ───────────────────────────────────────────────────────────────
    sub.add_parser("doctor", help="Full project health check").set_defaults(func=cmd_doctor)

    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
