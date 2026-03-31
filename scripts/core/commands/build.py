#!/usr/bin/env python3
"""
core/commands/build.py — Full build implementation.

This module contains the authoritative build implementation used by
`tool build`. Implementations previously lived in `scripts/build.py`.
"""
from __future__ import annotations

import argparse
import shutil
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
    list_presets,
    PROJECT_ROOT,
    json_read_cached,
    json_cache_clear,
)
from core.utils.common import get_project_version
from core.libpkg.jinja_helpers import render_template_file
import json

DEFAULT_PRESET = "gcc-debug-static-x86_64"

# Extension template configuration (kept small and safe)
EXT_DIR = PROJECT_ROOT / "extension"
TEMPLATE_DIR = EXT_DIR / "templates"

EXT_INCLUDE = [
    "CMakeLists.txt", "CMakePresets.json", "conanfile.py", "vcpkg.json",
    "Dockerfile", "LICENSE", "README.md", "AGENTS.md", "GEMINI.md",
    "MASTER_GENERATOR_PROMPT.md", "cmake", "apps", "libs", "tests", "scripts", "docs",
]

EXT_EXCLUDE = {
    "build", "build_logs", "__pycache__", ".cache", "extension",
}


def _is_excluded(rel: str) -> bool:
    # Normalize to forward slashes
    r = rel.replace("\\", "/")
    if r in EXT_EXCLUDE:
        return True
    for e in EXT_EXCLUDE:
        if r.startswith(e + "/"):
            return True
    return False


def _sync_templates() -> int:
    """Copy project files into extension templates directory, excluding dev files.
    Returns number of files copied."""
    # Incremental sync: avoid full removal/copy when files haven't changed.
    TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
    expected = set()
    copied = 0

    def _should_copy(src_path: Path, dst_path: Path) -> bool:
        if not dst_path.exists():
            return True
        try:
            s = src_path.stat()
            d = dst_path.stat()
            # If size and mtime match (to second), skip copy
            if s.st_size == d.st_size and int(s.st_mtime) == int(d.st_mtime):
                return False
        except Exception:
            return True
        return True

    for item in EXT_INCLUDE:
        src = PROJECT_ROOT / item
        if not src.exists():
            continue
        if src.is_file():
            rel = item
            if _is_excluded(rel):
                continue
            dst = TEMPLATE_DIR / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            expected.add(dst.relative_to(TEMPLATE_DIR).as_posix())
            if _should_copy(src, dst):
                try:
                    shutil.copy2(src, dst)
                    copied += 1
                except Exception:
                    pass
            continue
        # directory
        for f in src.rglob("*"):
            if f.is_file():
                rel = f.relative_to(PROJECT_ROOT).as_posix()
                if _is_excluded(rel):
                    continue
                dst = TEMPLATE_DIR / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                expected.add(dst.relative_to(TEMPLATE_DIR).as_posix())
                if _should_copy(f, dst):
                    try:
                        shutil.copy2(f, dst)
                        copied += 1
                    except Exception:
                        pass

    # Remove stale files that are not part of expected set
    try:
        for f in TEMPLATE_DIR.rglob("*"):
            if f.is_file():
                rel = f.relative_to(TEMPLATE_DIR).as_posix()
                if rel not in expected:
                    try:
                        f.unlink()
                    except Exception:
                        pass
    except Exception:
        pass

    Logger.info(f"Synced {copied} template files into {TEMPLATE_DIR}")
    return copied


def _sync_version() -> None:
    pkg = EXT_DIR / "package.json"
    if not pkg.exists():
        return
    try:
        data = json_read_cached(pkg, default={}) or {}
    except Exception:
        return
    ver = get_project_version()
    if data.get("version") != ver:
        data["version"] = ver
        pkg.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        try:
            json_cache_clear(pkg)
        except Exception:
            pass
        Logger.info(f"Synchronized extension version -> {ver}")


def _sync_license() -> None:
    src = PROJECT_ROOT / "LICENSE"
    dst = EXT_DIR / "LICENSE"
    if src.exists():
        shutil.copy2(src, dst)


def _choose_preset(preset: Optional[str]) -> str:
    if preset:
        return preset
    presets = list_presets()
    if presets:
        return presets[0]
    return DEFAULT_PRESET


def _generate_clang_tidy(profile: str) -> None:
    """Dynamically generate .clang-tidy based on build profile."""
    try:
        content = render_template_file("clang_tidy.jinja2", profile=profile)
        (PROJECT_ROOT / ".clang-tidy").write_text(content, encoding="utf-8")
        Logger.debug(f"Generated .clang-tidy for profile: {profile}")
    except Exception as e:
        Logger.warn(f"Failed to generate .clang-tidy: {e}")


def _impl_cmd_build(args) -> None:
    preset = _choose_preset(getattr(args, "preset", None))
    profile = getattr(args, "profile", "normal")
    sanitizers = getattr(args, "sanitizers", []) or []

    # Generate .clang-tidy before build starts
    _generate_clang_tidy(profile)

    extra_args = []
    
    # 1. Profile Logic (Hardening & Warnings)
    if profile == "extreme":
        Logger.warn("EXTREME profile active: Maximum hardening, no-exceptions, no-rtti, full RELRO.")
        extra_args += [
            "-DWARNING_LEVEL=ERROR",
            "-DHARDENING_LEVEL=EXTREME",
            "-DENABLE_CLANG_TIDY=ON",
            "-DENABLE_CPPCHECK=ON"
        ]
    elif profile == "hardened":
        Logger.warn("HARDENED profile active: Warnings are errors, security flags enabled.")
        extra_args += [
            "-DWARNING_LEVEL=ERROR",
            "-DHARDENING_LEVEL=STANDARD",
            "-DENABLE_CLANG_TIDY=ON",
            "-DENABLE_CPPCHECK=ON"
        ]
    elif profile == "strict":
        Logger.info("STRICT profile active: Aggressive warnings enabled.")
        extra_args += ["-DWARNING_LEVEL=AGGRESSIVE"]
    elif profile == "normal":
        Logger.debug("Applying 'normal' profile (default settings)")

    # 2. Sanitizer Logic
    if sanitizers:
        san_list = set(sanitizers)
        if "all" in san_list:
            Logger.warn("SANITIZED mode active: Enabling standard sanitizers (ASan + UBSan).")
            extra_args += ["-DENABLE_ASAN=ON", "-DENABLE_UBSAN=ON"]
        else:
            if "asan" in san_list:
                extra_args += ["-DENABLE_ASAN=ON"]
            if "ubsan" in san_list:
                extra_args += ["-DENABLE_UBSAN=ON"]
            if "tsan" in san_list:
                extra_args += ["-DENABLE_TSAN=ON"]
            Logger.warn(f"SANITIZED mode active: Enabled {', '.join(sorted(san_list))}")

        if "release" in preset.lower():
            Logger.warn(f"CAUTION: Sanitizers are enabled for a RELEASE build ({preset}). This is usually not recommended.")

    Logger.info(f"Configuring with preset '{preset}'")
    run_proc(["cmake", "--preset", preset] + extra_args)
    Logger.info("Building")
    run_proc(["cmake", "--build", "--preset", preset])


def _impl_cmd_check(args) -> None:
    preset = _choose_preset(getattr(args, "preset", None))
    _impl_cmd_build(args)
    Logger.info("Running tests")
    run_proc(["ctest", "--preset", preset, "--output-on-failure"])
    if not getattr(args, "no_sync", False):
        try:
            run_proc([sys.executable, str(PROJECT_ROOT / "scripts" / "tool.py"), "build", "extension"])
        except SystemExit:
            Logger.warn("Extension build failed (non-fatal)")


def _impl_cmd_clean(args) -> None:
    if getattr(args, "all", False):
        build_dir = PROJECT_ROOT / "build"
        if build_dir.exists():
            Logger.info("Removing build directory")
            shutil.rmtree(build_dir)
        return
    preset = _choose_preset(None)
    targets = getattr(args, "targets", []) or []
    if targets:
        for t in targets:
            run_proc(["cmake", "--build", "--preset", preset, "--target", t])
    else:
        run_proc(["cmake", "--build", "--preset", preset, "--target", "clean"])


def _impl_cmd_deploy(args) -> None:
    host = getattr(args, "host", None)
    path = getattr(args, "path", "/tmp/cpp_project")
    preset = getattr(args, "preset", None)
    if not host:
        Logger.error("Missing --host for deploy")
        raise SystemExit(2)
    build_dir = PROJECT_ROOT / "build" / (_choose_preset(preset))
    if not build_dir.exists():
        Logger.error("Build directory not found; run build first")
        raise SystemExit(2)
    if shutil.which("rsync"):
        run_proc(["rsync", "-avz", str(build_dir) + "/", f"{host}:{path}"])
    else:
        Logger.error("rsync not available")
        raise SystemExit(2)


def _impl_cmd_extension(args) -> None:
    ext_dir = PROJECT_ROOT / "extension"
    if not ext_dir.exists():
        Logger.error("extension/ directory not found")
        raise SystemExit(2)
    # Sync templates, version and license into extension/ before packaging
    try:
        _sync_templates()
        _sync_version()
        _sync_license()
    except Exception:
        Logger.warn("Template/version/license sync encountered an error (continuing)")
    # npm build (best-effort) — be tolerant if no `build` script exists
    pkg_json = ext_dir / "package.json"
    pkg_data = {}
    if pkg_json.exists():
        try:
            pkg_data = json.loads(pkg_json.read_text(encoding="utf-8"))
        except Exception:
            pkg_data = {}

    if pkg_json.exists() and shutil.which("npm"):
        try:
            run_proc(["npm", "ci"], cwd=ext_dir)
        except SystemExit:
            Logger.warn("npm ci failed (continuing)")
        scripts = pkg_data.get("scripts", {}) if isinstance(pkg_data, dict) else {}
        if "build" in scripts:
            try:
                run_proc(["npm", "run", "build"], cwd=ext_dir)
            except SystemExit:
                Logger.warn("npm run build failed (continuing)")
        else:
            Logger.info("No npm build script defined; skipping `npm run build`.")

    # Packaging: prefer system `vsce`, fallback to `npx vsce`, else skip
    packaged = False
    if shutil.which("vsce"):
        try:
            run_proc(["vsce", "package"], cwd=ext_dir)
            packaged = True
        except SystemExit:
            Logger.warn("vsce packaging failed (continuing)")
    elif shutil.which("npx"):
        try:
            run_proc(["npx", "vsce", "package", "--out", str(ext_dir)], cwd=ext_dir)
            packaged = True
        except SystemExit:
            Logger.warn("npx vsce package failed (continuing)")
    else:
        Logger.warn("vsce not found and npx not available; skipping .vsix packaging")

    if packaged:
        if getattr(args, "install", False):
            vsixs = list(ext_dir.glob("*.vsix"))
            if vsixs and shutil.which("code"):
                try:
                    run_proc(["code", "--install-extension", str(vsixs[0])], cwd=ext_dir)
                except SystemExit:
                    Logger.warn("code install-extension failed (continuing)")
        if getattr(args, "publish", False):
            if shutil.which("vsce"):
                try:
                    run_proc(["vsce", "publish"], cwd=ext_dir)
                except SystemExit:
                    Logger.warn("vsce publish failed (continuing)")
            elif shutil.which("npx"):
                try:
                    run_proc(["npx", "vsce", "publish"], cwd=ext_dir)
                except SystemExit:
                    Logger.warn("npx vsce publish failed (continuing)")


# ── Facade wrappers that return CLIResult ────────────────────────────────────


def cmd_build(args: argparse.Namespace) -> CLIResult:
    _generate_clang_tidy(getattr(args, "profile", "normal"))
    if GlobalConfig.DRY_RUN:
        Logger.info("[DRY-RUN] Would run: cmake --preset + cmake --build")
        return CLIResult(success=True, message="[DRY-RUN] build skipped")
    try:
        _impl_cmd_build(args)
        return CLIResult(success=True, message="Build complete.")
    except SystemExit as e:
        return CLIResult(success=(e.code == 0), code=e.code or 1, message="Build failed.")


def cmd_check(args: argparse.Namespace) -> CLIResult:
    _generate_clang_tidy(getattr(args, "profile", "normal"))
    if GlobalConfig.DRY_RUN:
        Logger.info("[DRY-RUN] Would run: cmake + build + ctest + extension sync")
        return CLIResult(success=True, message="[DRY-RUN] check skipped")
    try:
        _impl_cmd_check(args)
        return CLIResult(success=True, message="All checks passed.")
    except SystemExit as e:
        return CLIResult(success=(e.code == 0), code=e.code or 1, message="Check failed.")


def cmd_clean(args: argparse.Namespace) -> CLIResult:
    if GlobalConfig.DRY_RUN:
        Logger.info("[DRY-RUN] Would clean build artifacts")
        return CLIResult(success=True, message="[DRY-RUN] clean skipped")
    try:
        _impl_cmd_clean(args)
        return CLIResult(success=True, message="Clean done.")
    except SystemExit as e:
        return CLIResult(success=(e.code == 0), code=e.code or 1, message="Clean failed.")


def cmd_deploy(args: argparse.Namespace) -> CLIResult:
    if GlobalConfig.DRY_RUN:
        Logger.info(f"[DRY-RUN] Would deploy to {args.host}:{args.path}")
        return CLIResult(success=True, message="[DRY-RUN] deploy skipped")
    try:
        _impl_cmd_deploy(args)
        return CLIResult(success=True, message="Deploy complete.")
    except SystemExit as e:
        return CLIResult(success=(e.code == 0), code=e.code or 1, message="Deploy failed.")


def cmd_extension(args: argparse.Namespace) -> CLIResult:
    if GlobalConfig.DRY_RUN:
        Logger.info("[DRY-RUN] Would build .vsix extension")
        return CLIResult(success=True, message="[DRY-RUN] extension skipped")
    try:
        _impl_cmd_extension(args)
        return CLIResult(success=True, message="Extension built.")
    except SystemExit as e:
        return CLIResult(success=(e.code == 0), code=e.code or 1, message="Extension build failed.")


# ── Parser (mirrors previous build parser) ───────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tool build",
        description="Build system automation",
    )
    sub = parser.add_subparsers(dest="subcommand")

    # build
    p = sub.add_parser("build", help="Configure + compile")
    p.add_argument("--preset", default=None)
    p.add_argument("--profile", 
                   choices=["normal", "strict", "hardened", "extreme"], 
                   default="normal",
                   help="Apply specific build profile (e.g. hardened)")
    p.add_argument("--sanitizers", nargs="+",
                   choices=["asan", "ubsan", "tsan", "all"],
                   help="Enable granular sanitizers (multiple allowed, or 'all')")
    p.set_defaults(func=cmd_build)

    # check
    p = sub.add_parser("check", help="Build + test + extension sync")
    p.add_argument("--preset", default=None)
    p.add_argument("--profile", 
                   choices=["normal", "strict", "hardened", "extreme"], 
                   default="normal",
                   help="Apply specific build profile (e.g. hardened)")
    p.add_argument("--sanitizers", nargs="+",
                   choices=["asan", "ubsan", "tsan", "all"],
                   help="Enable granular sanitizers (multiple allowed, or 'all')")
    p.add_argument("--no-sync", action="store_true")
    p.set_defaults(func=cmd_check)

    # clean
    p = sub.add_parser("clean", help="Remove build artifacts")
    p.add_argument("targets", nargs="*")
    p.add_argument("--all", action="store_true")
    p.set_defaults(func=cmd_clean)

    # deploy
    p = sub.add_parser("deploy", help="Remote deploy via rsync")
    p.add_argument("--host", required=True)
    p.add_argument("--path", default="/tmp/cpp_project")
    p.add_argument("--preset", default=None)
    p.set_defaults(func=cmd_deploy)

    # extension
    p = sub.add_parser("extension", help="Build .vsix extension")
    p.add_argument("--install", action="store_true")
    p.add_argument("--publish", action="store_true")
    p.set_defaults(func=cmd_extension)

    return parser


def main(argv: list[str]) -> None:
    parser = build_parser()
    # Default subcommand: "build"
    args = parser.parse_args(argv if argv else ["build"])
    if hasattr(args, "func"):
        args.func(args).exit()
    else:
        parser.print_help()
