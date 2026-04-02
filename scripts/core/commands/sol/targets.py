"""Target and preset management subcommands."""
from __future__ import annotations

import sys

from core.utils.common import Logger, PROJECT_ROOT, run_proc, GlobalConfig
from core.utils.command_utils import wrap_command
from ._helpers import (
    load_presets,
    save_presets,
    _make_preset_name,
    VALID_COMPILERS,
    VALID_TYPES,
    VALID_LINKS,
    _BUILD_TYPE,
    _SHARED,
)


# ── Target commands ───────────────────────────────────────────────────────────

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
        # Write CMakeLists.txt. Use the configured repository base version
        # (strip any +revision metadata) so generated apps stay in sync.
        base_ver = GlobalConfig.VERSION.split("+")[0] if GlobalConfig.VERSION else "0.0.0"
        cm_content = (
            f"cmake_minimum_required(VERSION 3.25)\n"
            f"project({name} VERSION {base_ver} LANGUAGES CXX)\n\n"
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


# ── Preset commands ───────────────────────────────────────────────────────────

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


# ── Wrapper functions ─────────────────────────────────────────────────────────

def cmd_target_list(args):
    return wrap_command(_impl_cmd_target_list, args)


def cmd_target_build(args):
    return wrap_command(_impl_cmd_target_build, args)


def cmd_target_add(args):
    return wrap_command(_impl_cmd_target_add, args)


def cmd_preset_list(args):
    return wrap_command(_impl_cmd_preset_list, args)


def cmd_preset_add(args):
    return wrap_command(_impl_cmd_preset_add, args)


def cmd_preset_remove(args):
    return wrap_command(_impl_cmd_preset_remove, args)
