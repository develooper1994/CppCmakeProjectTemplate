"""
core/commands/presets.py — CMakePresets.json generator
=======================================================

Generates a complete CMakePresets.json file from the [presets] section of
tool.toml, covering the full <compiler>-<buildtype>-<linkage>-<arch> matrix.

Subcommands
-----------
  generate   Build and (optionally) write CMakePresets.json
  list       List presets from the *current* CMakePresets.json
  validate   Run `cmake --list-presets` to verify the file

Usage
-----
  tool presets generate
  tool presets generate --compiler gcc --arch x86_64 --dry-run
  tool presets generate --compiler cuda
  tool presets generate --output /tmp/presets.json --no-backup
  tool presets list
  tool presets validate
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Locate project root (the directory that contains CMakeLists.txt)
# ---------------------------------------------------------------------------
_THIS = Path(__file__).resolve()
_SCRIPTS = _THIS.parent.parent.parent          # scripts/
PROJECT_ROOT = _SCRIPTS.parent                  # project root
PRESETS_PATH = PROJECT_ROOT / "CMakePresets.json"
TOOL_TOML   = PROJECT_ROOT / "tool.toml"

# ---------------------------------------------------------------------------
# Build-type → CMake BUILD_TYPE string
# ---------------------------------------------------------------------------
_BUILD_TYPE_MAP: dict[str, str] = {
    "debug":          "Debug",
    "release":        "Release",
    "relwithdebinfo": "RelWithDebInfo",
    "minsizerel":     "MinSizeRel",
}

# Build-type → MSVC configuration name
_MSVC_CONFIG_MAP: dict[str, str] = {
    "debug":          "Debug",
    "release":        "Release",
    "relwithdebinfo": "RelWithDebInfo",
    "minsizerel":     "MinSizeRel",
}

# Arch → MSVC architecture string (Visual Studio generator)
_MSVC_ARCH_MAP: dict[str, str] = {
    "x86_64": "x64",
    "x64":    "x64",
    "x86":    "Win32",
    "win32":  "Win32",
}


# ---------------------------------------------------------------------------
# Load [presets] from tool.toml
# ---------------------------------------------------------------------------

def _load_toml_section(toml_path: Path, section: str) -> dict[str, Any]:
    """Very small TOML parser — handles the flat key=value style we use."""
    try:
        import tomllib  # Python 3.11+
    except ImportError:
        try:
            import tomli as tomllib  # pip install tomli
        except ImportError:
            return _fallback_parse(toml_path, section)

    with open(toml_path, "rb") as fh:
        data = tomllib.load(fh)
    return data.get(section, {})


def _fallback_parse(toml_path: Path, section: str) -> dict[str, Any]:
    """
    Minimal line-by-line TOML parser — handles list and scalar values
    in a named section. Used when tomllib/tomli are unavailable.
    """
    result: dict[str, Any] = {}
    in_section = False
    accumulating_list = False
    list_key = ""
    list_vals: list[str] = []

    with open(toml_path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()

            # Section header [name]
            if re.match(r"^\[[\w.]+\]$", line):
                # Flush any in-progress list
                if accumulating_list:
                    result[list_key] = list_vals
                    accumulating_list = False
                    list_vals = []
                in_section = (line == f"[{section}]")
                continue

            if not in_section or not line or line.startswith("#"):
                continue

            # Multi-line list continuation: "  \"val\","
            if accumulating_list:
                # collect quoted values
                for match in re.finditer(r'"([^"]+)"', line):
                    list_vals.append(match.group(1))
                if "]" in line:
                    result[list_key] = list_vals
                    accumulating_list = False
                    list_vals = []
                continue

            if "=" not in line:
                continue

            key, _, val_raw = line.partition("=")
            key = key.strip()
            val_raw = val_raw.strip()

            # Strip inline comments
            val_raw = re.sub(r"\s*#.*$", "", val_raw).strip()

            # Boolean
            if val_raw.lower() in ("true", "false"):
                result[key] = val_raw.lower() == "true"
            # Integer
            elif re.match(r"^-?\d+$", val_raw):
                result[key] = int(val_raw)
            # Float
            elif re.match(r"^-?\d+\.\d+$", val_raw):
                result[key] = float(val_raw)
            # Inline single-line list: ["a", "b"]
            elif val_raw.startswith("[") and "]" in val_raw:
                result[key] = re.findall(r'"([^"]+)"', val_raw)
            # Multi-line list start: [
            elif val_raw == "[":
                list_key = key
                list_vals = []
                accumulating_list = True
            # Quoted string
            elif val_raw.startswith('"') and val_raw.endswith('"'):
                result[key] = val_raw[1:-1]
            else:
                result[key] = val_raw

    if accumulating_list:
        result[list_key] = list_vals

    return result


def _load_config() -> dict[str, Any]:
    cfg = _load_toml_section(TOOL_TOML, "presets")
    # Provide safe defaults for every key
    defaults: dict[str, Any] = {
        "compilers":           ["gcc", "clang"],
        "build_types":         ["debug", "release", "relwithdebinfo"],
        "linkages":            ["static", "dynamic"],
        "arches":              ["x86_64"],
        "cmake_minimum_major": 3,
        "cmake_minimum_minor": 25,
        "default_preset":      "gcc-debug-static-x86_64",
        "cuda_architectures":  "native",
        "generator":           "Ninja",
        "skip_combinations":   [],
    }
    defaults.update(cfg)
    return defaults


# ---------------------------------------------------------------------------
# Constraint / skip logic
# ---------------------------------------------------------------------------

def _should_skip(compiler: str, build_type: str, linkage: str, arch: str,
                 skip_patterns: list[str]) -> str | None:
    """Return a reason string if this combination should be skipped, else None."""
    name = f"{compiler}-{build_type}-{linkage}-{arch}"

    # Hard rules
    if compiler == "cuda" and linkage == "dynamic":
        return "CUDA compiler forces static linkage"
    if compiler == "msvc":
        if arch not in ("x86_64", "x64", "x86", "win32"):
            return f"MSVC preset not generated for non-Windows arch '{arch}'"

    # User-configured patterns  (tool.toml  skip_combinations)
    for pattern in skip_patterns:
        # Normalise pattern segments to match our naming
        if fnmatch.fnmatch(name, pattern):
            return f"matches skip pattern '{pattern}'"

    return None


# ---------------------------------------------------------------------------
# Toolchain helpers
# ---------------------------------------------------------------------------

def _toolchain_for(arch: str) -> str | None:
    """Return relative toolchain path for non-native arches, or None."""
    native = {"x86_64", "x64"}
    if arch in native:
        return None
    tc = PROJECT_ROOT / "cmake" / "toolchains" / f"{arch}.cmake"
    if tc.exists():
        return "${sourceDir}/cmake/toolchains/" + tc.name
    # fallback: assume the caller knows what they're doing
    return "${sourceDir}/cmake/toolchains/" + arch + ".cmake"


# ---------------------------------------------------------------------------
# Preset builders
# ---------------------------------------------------------------------------

def _base_presets(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    """Build the hidden base presets that all concrete presets inherit."""
    generator = cfg.get("generator", "Ninja")

    presets = [
        {
            "name": "base",
            "hidden": True,
            "binaryDir": "${sourceDir}/build/${presetName}",
            "cacheVariables": {
                "CMAKE_EXPORT_COMPILE_COMMANDS": "ON",
                "ENABLE_UNIT_TESTS": "ON",
            },
        },
        {
            "name": "linux-base",
            "hidden": True,
            "inherits": "base",
            "generator": generator,
            "condition": {
                "type": "anyOf",
                "conditions": [
                    {"type": "equals", "lhs": "${hostSystemName}", "rhs": "Linux"},
                    {"type": "equals", "lhs": "${hostSystemName}", "rhs": "Darwin"},
                ],
            },
        },
        {
            "name": "linux-gcc-base",
            "hidden": True,
            "inherits": "linux-base",
            "cacheVariables": {
                "CMAKE_C_COMPILER": "gcc",
                "CMAKE_CXX_COMPILER": "g++",
            },
        },
        {
            "name": "linux-clang-base",
            "hidden": True,
            "inherits": "linux-base",
            "cacheVariables": {
                "CMAKE_C_COMPILER": "clang",
                "CMAKE_CXX_COMPILER": "clang++",
            },
        },
        {
            "name": "linux-cuda-base",
            "hidden": True,
            "inherits": "linux-base",
            "cacheVariables": {
                "CMAKE_C_COMPILER": "gcc",
                "CMAKE_CXX_COMPILER": "g++",
                "ENABLE_CUDA": "ON",
                "CMAKE_CUDA_ARCHITECTURES": cfg["cuda_architectures"],
            },
        },
        {
            "name": "win-base",
            "hidden": True,
            "inherits": "base",
            "generator": "Visual Studio 17 2022",
            "condition": {
                "type": "equals",
                "lhs": "${hostSystemName}",
                "rhs": "Windows",
            },
        },
    ]
    return presets


def _concrete_configure_presets(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    """Build concrete configurePresets from the full matrix."""
    compilers   = [c.lower() for c in cfg["compilers"]]
    build_types = [b.lower() for b in cfg["build_types"]]
    linkages    = [l.lower() for l in cfg["linkages"]]
    arches      = [a.lower() for a in cfg["arches"]]
    skip_pats   = cfg.get("skip_combinations", [])

    presets: list[dict[str, Any]] = []

    for compiler in compilers:
        for build_type in build_types:
            for linkage in linkages:
                for arch in arches:
                    reason = _should_skip(compiler, build_type, linkage, arch, skip_pats)
                    if reason:
                        print(f"  [skip] {compiler}-{build_type}-{linkage}-{arch}: {reason}",
                              file=sys.stderr)
                        continue

                    preset = _make_configure_preset(
                        compiler, build_type, linkage, arch, cfg)
                    if preset:
                        presets.append(preset)

    return presets


def _make_configure_preset(
    compiler: str,
    build_type: str,
    linkage: str,
    arch: str,
    cfg: dict[str, Any],
) -> dict[str, Any] | None:
    """Create one configurePreset entry."""
    bt_cmake = _BUILD_TYPE_MAP.get(build_type, build_type.capitalize())
    shared   = "ON" if linkage == "dynamic" else "OFF"

    # --- Build preset name ---
    name = f"{compiler}-{build_type}-{linkage}-{arch}"
    display = f"{compiler.upper()} {bt_cmake} {linkage.capitalize()}: {arch}"

    cache_vars: dict[str, str] = {
        "CMAKE_BUILD_TYPE": bt_cmake,
        "BUILD_SHARED_LIBS": shared,
    }

    # MSVC path
    if compiler == "msvc":
        msvc_arch = _MSVC_ARCH_MAP.get(arch, "x64")
        preset: dict[str, Any] = {
            "name": name,
            "displayName": display,
            "inherits": "win-base",
            "architecture": msvc_arch,
            "cacheVariables": cache_vars,
        }
        return preset

    # CUDA path
    if compiler == "cuda":
        cache_vars["ENABLE_CUDA"] = "ON"
        cache_vars["CMAKE_CUDA_ARCHITECTURES"] = cfg["cuda_architectures"]
        base = "linux-cuda-base"
    elif compiler == "gcc":
        base = "linux-gcc-base"
    elif compiler == "clang":
        base = "linux-clang-base"
    else:
        # Unknown compiler — try to use a base named linux-<compiler>-base
        base = f"linux-{compiler}-base"

    preset = {
        "name": name,
        "displayName": display,
        "inherits": base,
        "cacheVariables": cache_vars,
    }

    # Cross-compilation toolchain for non-native arches
    tc = _toolchain_for(arch)
    if tc:
        preset["toolchainFile"] = tc
        # Tests typically can't run on the host for cross-compiled targets
        cache_vars["ENABLE_UNIT_TESTS"] = "OFF"

    return preset


def _build_presets(configure_names: list[str]) -> list[dict[str, Any]]:
    """Generate one buildPreset per configurePreset."""
    result = []
    for name in configure_names:
        entry: dict[str, Any] = {
            "name": name,
            "configurePreset": name,
        }
        # MSVC multi-config: add "configuration"
        parts = name.split("-")
        if parts[0] == "msvc" and len(parts) >= 2:
            bt = parts[1]
            entry["configuration"] = _MSVC_CONFIG_MAP.get(bt, bt.capitalize())
        result.append(entry)
    return result


def _test_presets(configure_names: list[str]) -> list[dict[str, Any]]:
    """Generate one testPreset per configurePreset (skip cross-compiled)."""
    result = []
    for name in configure_names:
        # Skip cross-compiled presets (they have ENABLE_UNIT_TESTS=OFF)
        parts = name.split("-")
        arch = parts[-1] if parts else ""
        native_arches = {"x86_64", "x64"}
        if arch not in native_arches:
            continue
        # Skip embedded
        if name.startswith("embedded"):
            continue

        entry: dict[str, Any] = {
            "name": name,
            "configurePreset": name,
        }
        # MSVC
        if parts[0] == "msvc" and len(parts) >= 2:
            bt = parts[1]
            entry["configuration"] = _MSVC_CONFIG_MAP.get(bt, bt.capitalize())
        result.append(entry)
    return result


# ---------------------------------------------------------------------------
# Generator entry point
# ---------------------------------------------------------------------------

def _generate(args: argparse.Namespace) -> int:
    cfg = _load_config()

    # Apply CLI filters
    if args.compiler:
        cfg["compilers"] = [c.strip() for c in args.compiler.split(",")]
    if args.build_type:
        cfg["build_types"] = [b.strip() for b in args.build_type.split(",")]
    if args.linkage:
        cfg["linkages"] = [l.strip() for l in args.linkage.split(",")]
    if args.arch:
        cfg["arches"] = [a.strip() for a in args.arch.split(",")]

    out_path = Path(args.output) if args.output else PRESETS_PATH

    # --- Build preset sections ---
    base_cfg   = _base_presets(cfg)
    concrete   = _concrete_configure_presets(cfg)
    all_cfg    = base_cfg + concrete
    all_names  = [p["name"] for p in concrete]

    builds  = _build_presets(all_names)
    tests   = _test_presets(all_names)

    maj = int(cfg.get("cmake_minimum_major", 3))
    min_ = int(cfg.get("cmake_minimum_minor", 25))

    document: dict[str, Any] = {
        "version": 4,
        "cmakeMinimumRequired": {"major": maj, "minor": min_, "patch": 0},
        "vendor": {
            "tool-presets-generator": {
                "generated": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                "note": "AUTO-GENERATED — DO NOT EDIT MANUALLY. Edit tool.toml [presets] and re-run `tool presets generate`.",
            }
        },
        "configurePresets": all_cfg,
        "buildPresets": builds,
        "testPresets": tests,
    }

    json_text = json.dumps(document, indent=2) + "\n"

    # --- Dry run ---
    if args.dry_run:
        print(json_text)
        print(f"\n[dry-run] Would write {len(all_cfg)} configurePresets "
              f"({len(base_cfg)} hidden + {len(concrete)} concrete), "
              f"{len(builds)} buildPresets, {len(tests)} testPresets.",
              file=sys.stderr)
        return 0

    # --- Backup ---
    do_backup = not args.no_backup
    if do_backup and out_path.exists():
        bak = out_path.with_suffix(".json.bak")
        shutil.copy2(out_path, bak)
        print(f"[presets] Backup saved: {bak}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json_text, encoding="utf-8")
    print(f"[presets] Written: {out_path}  "
          f"({len(concrete)} concrete presets + {len(base_cfg)} hidden bases)")
    return 0


# ---------------------------------------------------------------------------
# List subcommand
# ---------------------------------------------------------------------------

def _list_presets(_args: argparse.Namespace) -> int:
    if not PRESETS_PATH.exists():
        print(f"[presets] No CMakePresets.json at {PRESETS_PATH}", file=sys.stderr)
        return 1

    with open(PRESETS_PATH, encoding="utf-8") as fh:
        doc = json.load(fh)

    cfg_presets  = doc.get("configurePresets", [])
    bld_presets  = doc.get("buildPresets", [])
    tst_presets  = doc.get("testPresets", [])

    visible = [p for p in cfg_presets if not p.get("hidden", False)]
    hidden  = [p for p in cfg_presets if p.get("hidden", False)]

    print(f"CMakePresets.json  (version {doc.get('version', '?')})")
    print(f"  configurePresets : {len(visible)} visible + {len(hidden)} hidden")
    print(f"  buildPresets     : {len(bld_presets)}")
    print(f"  testPresets      : {len(tst_presets)}")
    print()
    for p in visible:
        display = p.get("displayName", "")
        suffix = f"  [{display}]" if display else ""
        print(f"  {p['name']}{suffix}")
    return 0


# ---------------------------------------------------------------------------
# Validate subcommand
# ---------------------------------------------------------------------------

def _validate(_args: argparse.Namespace) -> int:
    if not PRESETS_PATH.exists():
        print(f"[presets] No CMakePresets.json at {PRESETS_PATH}", file=sys.stderr)
        return 1

    cmake = shutil.which("cmake")
    if not cmake:
        print("[presets] cmake not found in PATH — cannot validate.", file=sys.stderr)
        return 1

    try:
        result = subprocess.run(
            [cmake, "--list-presets"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        print("[presets] cmake --list-presets timed out after 30 s", file=sys.stderr)
        return 1

    if result.returncode != 0:
        print("[presets] Validation FAILED:")
        print(result.stderr)
        return result.returncode

    print("[presets] Validation OK — cmake --list-presets:")
    print(result.stdout)
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser(parent: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = parent.add_parser("presets", help="Generate and manage CMakePresets.json")
    sub = p.add_subparsers(dest="presets_cmd")

    # -- generate --
    gen = sub.add_parser("generate",
        help="Generate CMakePresets.json from tool.toml [presets]")
    gen.add_argument("--compiler",   metavar="C[,C2]",
        help="Comma-separated compiler filter: gcc, clang, cuda, msvc")
    gen.add_argument("--build-type", metavar="T[,T2]",
        help="Comma-separated build-type filter: debug, release, relwithdebinfo")
    gen.add_argument("--linkage",    metavar="L[,L2]",
        help="Comma-separated linkage filter: static, dynamic")
    gen.add_argument("--arch",       metavar="A[,A2]",
        help="Comma-separated arch filter: x86_64, x86, aarch64, ...")
    gen.add_argument("--output",     metavar="PATH",
        help=f"Output path (default: {PRESETS_PATH.name})")
    gen.add_argument("--dry-run",    action="store_true",
        help="Print the generated JSON to stdout without writing")
    gen.add_argument("--no-backup",  action="store_true",
        help="Skip CMakePresets.json.bak before overwriting")

    # -- list --
    sub.add_parser("list", help="List presets from CMakePresets.json")

    # -- validate --
    sub.add_parser("validate",
        help="Validate CMakePresets.json using `cmake --list-presets`")


def main(argv: list[str] | None = None) -> int:
    """Entry-point when called as `tool presets <cmd>`."""
    parser = argparse.ArgumentParser(prog="tool presets")
    sub = parser.add_subparsers(dest="presets_cmd")

    # Inline reuse of build_parser logic
    gen = sub.add_parser("generate")
    gen.add_argument("--compiler")
    gen.add_argument("--build-type")
    gen.add_argument("--linkage")
    gen.add_argument("--arch")
    gen.add_argument("--output")
    gen.add_argument("--dry-run", action="store_true")
    gen.add_argument("--no-backup", action="store_true")

    sub.add_parser("list")
    sub.add_parser("validate")

    args = parser.parse_args(argv)

    if args.presets_cmd == "generate":
        return _generate(args)
    elif args.presets_cmd == "list":
        return _list_presets(args)
    elif args.presets_cmd == "validate":
        return _validate(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
