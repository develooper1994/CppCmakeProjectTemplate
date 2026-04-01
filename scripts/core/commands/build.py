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
    run_capture,
    list_presets,
    PROJECT_ROOT,
    json_read_cached,
    json_cache_clear,
)
from core.utils.common import get_project_version, get_project_name
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

    # LTO
    if getattr(args, "lto", False):
        extra_args.append("-DENABLE_LTO=ON")
        Logger.info("LTO enabled for this build")

    # PGO
    pgo_mode = getattr(args, "pgo", None)
    if pgo_mode:
        extra_args.append(f"-DPGO_MODE={pgo_mode}")
        pgo_dir = getattr(args, "pgo_dir", None)
        if pgo_dir:
            extra_args.append(f"-DPGO_PROFILE_DIR={pgo_dir}")
        Logger.info(f"PGO mode: {pgo_mode}")

    # BOLT
    if getattr(args, "bolt", False):
        extra_args.append("-DENABLE_BOLT=ON")
        Logger.info("BOLT post-link optimization targets enabled (use bolt-instrument-<target> / bolt-optimize-<target> targets)")

    # OpenMP
    if getattr(args, "openmp", False):
        extra_args.append("-DENABLE_OPENMP=ON")
        Logger.info("OpenMP threading enabled")
    if getattr(args, "openmp_simd", False):
        extra_args.append("-DENABLE_OPENMP_SIMD=ON")
        Logger.info("OpenMP SIMD-only enabled")
    if getattr(args, "auto_parallel", False):
        extra_args.append("-DENABLE_AUTO_PARALLEL=ON")
        Logger.info("Auto-parallelization enabled")

    # Qt
    if getattr(args, "qt", False):
        extra_args.append("-DENABLE_QT=ON")
        Logger.info("Qt support enabled (auto-detects Qt6/Qt5)")
    if getattr(args, "qml", False):
        extra_args.append("-DENABLE_QT=ON")
        extra_args.append("-DENABLE_QML=ON")
        Logger.info("Qt QML/Quick support enabled")

    # Reproducible build
    if getattr(args, "reproducible", False):
        extra_args.append("-DENABLE_REPRODUCIBLE=ON")
        Logger.info("Reproducible build enabled (source paths stripped, deterministic ar)")

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
    # Write a build configuration summary to disk so CI and humans can inspect
    try:
        def _write_build_summary(profile, preset, sanitizers, extra_args):
            out = {
                "profile": profile,
                "preset": preset,
                "sanitizers": list(sanitizers) if sanitizers else [],
                "extra_args": extra_args,
                "project": get_project_name(),
                "version": get_project_version(),
            }
            # Try to add git metadata
            try:
                gd, rc = run_capture(["git", "describe", "--tags", "--always", "--dirty"], cwd=PROJECT_ROOT)
                out["git_describe"] = gd if rc == 0 else "N/A"
                gh, rc2 = run_capture(["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT)
                out["git_hash"] = gh if rc2 == 0 else "N/A"
            except Exception:
                out["git_describe"] = "N/A"
                out["git_hash"] = "N/A"

            # Effective toggles derived from extra_args
            toggles = {}
            toggles["ENABLE_ASAN"] = any(a.startswith("-DENABLE_ASAN=") or a == "-DENABLE_ASAN=ON" for a in extra_args)
            toggles["ENABLE_UBSAN"] = any(a.startswith("-DENABLE_UBSAN=") or a == "-DENABLE_UBSAN=ON" for a in extra_args)
            toggles["ENABLE_TSAN"] = any(a.startswith("-DENABLE_TSAN=") or a == "-DENABLE_TSAN=ON" for a in extra_args)
            toggles["ENABLE_CLANG_TIDY"] = any(a.startswith("-DENABLE_CLANG_TIDY=") or a == "-DENABLE_CLANG_TIDY=ON" for a in extra_args)
            toggles["HARDENING_LEVEL"] = next((a.split('=')[1] for a in extra_args if a.startswith("-DHARDENING_LEVEL=")), "(unset)")
            toggles["ENABLE_LTO"] = any(a == "-DENABLE_LTO=ON" for a in extra_args)
            toggles["PGO_MODE"] = next((a.split('=')[1] for a in extra_args if a.startswith("-DPGO_MODE=")), "(off)")
            out["toggles"] = toggles

            # Ensure build dir exists
            build_dir = PROJECT_ROOT / "build"
            build_dir.mkdir(parents=True, exist_ok=True)
            path = build_dir / "build_config.json"
            import json
            path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
            return path

        summary_path = _write_build_summary(profile, preset, sanitizers, extra_args)
        Logger.info(f"Build Configuration Summary written to: {summary_path}")
    except Exception as e:
        Logger.warn(f"Failed to write build configuration summary: {e}")

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


def cmd_docker(args: argparse.Namespace) -> CLIResult:
    if GlobalConfig.DRY_RUN:
        Logger.info("[DRY-RUN] Would run: docker run ... python3 scripts/tool.py build build")
        return CLIResult(success=True, message="[DRY-RUN] docker skipped")
    try:
        _impl_cmd_docker(args)
        return CLIResult(success=True, message="Docker build complete.")
    except SystemExit as e:
        return CLIResult(success=(e.code == 0), code=e.code or 1, message="Docker build failed.")


def _impl_cmd_docker(args) -> None:
    """Run the project build inside a Docker container.

    Mounts the workspace read-write at /workspace inside the container, then
    calls `python3 scripts/tool.py build build [--preset <preset>] [extra]`.
    The container is removed after the run (--rm).
    """
    docker_bin = shutil.which("docker")
    if not docker_bin:
        Logger.error("docker not found in PATH.  Install Docker to use this subcommand.")
        raise SystemExit(1)

    image = getattr(args, "image", "ubuntu:24.04") or "ubuntu:24.04"
    preset = getattr(args, "preset", None)
    extra_args: list[str] = list(getattr(args, "extra_args", []) or [])

    inner_cmd = ["python3", "scripts/tool.py", "build", "build"]
    if preset:
        inner_cmd += ["--preset", preset]
    inner_cmd.extend(extra_args)

    docker_cmd = [
        docker_bin, "run", "--rm",
        "-v", f"{PROJECT_ROOT}:/workspace",
        "-w", "/workspace",
        image,
    ] + inner_cmd

    Logger.info(f"[Docker] Image : {image}")
    Logger.info(f"[Docker] Preset: {preset or '(auto)'}")
    Logger.info(f"[Docker] Cmd   : {' '.join(inner_cmd)}")
    run_proc(docker_cmd)


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
    p.add_argument("--lto", action="store_true", help="Enable Link-Time Optimization")
    p.add_argument("--pgo", choices=["generate", "use"], default=None,
                   help="Profile-Guided Optimization mode")
    p.add_argument("--pgo-dir", default=None, metavar="DIR",
                   help="PGO profile data directory (default: build/pgo-profiles)")
    p.add_argument("--bolt", action="store_true",
                   help="Enable LLVM BOLT post-link optimization targets (requires llvm-bolt)")
    p.add_argument("--openmp", action="store_true", help="Enable OpenMP threading (-DENABLE_OPENMP=ON)")
    p.add_argument("--openmp-simd", action="store_true", dest="openmp_simd",
                   help="Enable OpenMP SIMD only — no libgomp runtime dep (-DENABLE_OPENMP_SIMD=ON)")
    p.add_argument("--auto-parallel", action="store_true", dest="auto_parallel",
                   help="Enable compiler auto-parallelization (-DENABLE_AUTO_PARALLEL=ON)")
    p.add_argument("--qt", action="store_true", help="Enable Qt support (-DENABLE_QT=ON)")
    p.add_argument("--qml", action="store_true", help="Enable Qt QML/Quick (-DENABLE_QT=ON -DENABLE_QML=ON)")
    p.add_argument("--reproducible", action="store_true",
                   help="Enable binary reproducibility (-DENABLE_REPRODUCIBLE=ON)")
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
    p.add_argument("--lto", action="store_true", help="Enable Link-Time Optimization")
    p.add_argument("--pgo", choices=["generate", "use"], default=None,
                   help="Profile-Guided Optimization mode")
    p.add_argument("--pgo-dir", default=None, metavar="DIR",
                   help="PGO profile data directory")
    p.add_argument("--bolt", action="store_true",
                   help="Enable LLVM BOLT post-link optimization targets (requires llvm-bolt)")
    p.add_argument("--openmp", action="store_true", help="Enable OpenMP threading")
    p.add_argument("--openmp-simd", action="store_true", dest="openmp_simd",
                   help="Enable OpenMP SIMD only")
    p.add_argument("--auto-parallel", action="store_true", dest="auto_parallel",
                   help="Enable compiler auto-parallelization")
    p.add_argument("--qt", action="store_true", help="Enable Qt support")
    p.add_argument("--qml", action="store_true", help="Enable Qt QML/Quick")
    p.add_argument("--reproducible", action="store_true",
                   help="Enable binary reproducibility (-DENABLE_REPRODUCIBLE=ON)")
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

    # docker
    p = sub.add_parser("docker", help="Build inside a Docker container")
    p.add_argument("--preset", default=None, help="CMake preset to pass (default: auto-detected)")
    p.add_argument("--image", default="ubuntu:24.04",
                   help="Docker image to use (default: ubuntu:24.04)")
    p.add_argument("--extra-args", nargs=argparse.REMAINDER, default=[],
                   metavar="ARG", dest="extra_args",
                   help="Extra arguments forwarded to 'tool build build' inside container")
    p.set_defaults(func=cmd_docker)

    return parser


def main(argv: list[str]) -> None:
    parser = build_parser()
    # Default subcommand: "build"
    args = parser.parse_args(argv if argv else ["build"])
    if hasattr(args, "func"):
        args.func(args).exit()
    else:
        parser.print_help()
