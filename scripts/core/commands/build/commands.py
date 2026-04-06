"""Build command implementations and CLIResult wrappers."""
from __future__ import annotations

import argparse
import json
import shutil
import sys

from core.utils.common import (
    Logger,
    GlobalConfig,
    CLIResult,
    run_proc,
    run_capture,
    PROJECT_ROOT,
    get_project_version,
    get_project_name,
)
from ._helpers import (
    _choose_preset,
    _generate_clang_tidy,
    _sync_version,
    _sync_license,
)


# ── Implementation functions ──────────────────────────────────────────────────

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

    # Optional allocator backend
    allocator = getattr(args, "allocator", "default")
    if allocator and allocator != "default":
        extra_args.append(f"-DENABLE_ALLOCATOR={allocator}")
        extra_args.append("-DENABLE_ALLOCATOR_OVERRIDE_ALL=ON")
        Logger.info(f"Allocator backend enabled: {allocator}")
    else:
        # Avoid sticky cache state from previous non-default allocator runs.
        extra_args.append("-DENABLE_ALLOCATOR=default")
        extra_args.append("-DENABLE_ALLOCATOR_OVERRIDE_ALL=OFF")

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
    # Analyzer flags (opt-in via CLI)
    if getattr(args, "enable_gcc_analyzer", False):
        extra_args.append("-DENABLE_GCC_ANALYZER=ON")
        Logger.info("GCC -fanalyzer enabled for this build (opt-in)")
    if getattr(args, "enable_msvc_analyze", False):
        extra_args.append("-DENABLE_MSVC_ANALYZE=ON")
        Logger.info("MSVC /analyze enabled for this build (opt-in)")
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
        # Directories to remove
        dirs_to_remove = [
            "build", "build-extreme", "build_logs",
            "dist", ".tool",
            ".mypy_cache", ".pytest_cache", ".ruff_cache",
            "extension/templates", "extension/node_modules",
        ]
        removed = []
        for name in dirs_to_remove:
            d = PROJECT_ROOT / name
            if d.exists():
                shutil.rmtree(d)
                removed.append(name)

        # Glob patterns for files at project root
        file_globs = ["*.egg-info", "conan.lock"]
        for pattern in file_globs:
            for f in PROJECT_ROOT.glob(pattern):
                if f.is_dir():
                    shutil.rmtree(f)
                else:
                    f.unlink()
                removed.append(f.name)

        # *.vsix in extension/
        ext_dir = PROJECT_ROOT / "extension"
        if ext_dir.exists():
            for f in ext_dir.glob("*.vsix"):
                f.unlink()
                removed.append(f"extension/{f.name}")

        # Recursive __pycache__ cleanup
        pycache_count = 0
        for pc in PROJECT_ROOT.rglob("__pycache__"):
            if pc.is_dir():
                shutil.rmtree(pc)
                pycache_count += 1
        if pycache_count:
            removed.append(f"__pycache__ ({pycache_count} dirs)")

        if removed:
            Logger.info(f"Removed: {', '.join(removed)}")
        else:
            Logger.info("Nothing to clean")
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
    # Sync version and license into extension/ before packaging
    try:
        _sync_version()
        _sync_license()
    except Exception:
        Logger.warn("Version/license sync encountered an error (continuing)")
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


def _impl_cmd_docker(args) -> None:
    """Run the project build inside a Docker container."""
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


# ── CLIResult wrapper functions ───────────────────────────────────────────────

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


# ── Watch mode ────────────────────────────────────────────────────────────────

def _impl_cmd_watch(args) -> None:
    """Watch source directories and auto-rebuild on changes."""
    import platform
    import time

    preset = _choose_preset(getattr(args, "preset", None))
    interval = getattr(args, "interval", 2)

    watch_dirs = [
        PROJECT_ROOT / "libs",
        PROJECT_ROOT / "apps",
        PROJECT_ROOT / "cmake",
    ]
    extensions = {".cpp", ".hpp", ".h", ".cxx", ".cc", ".cmake", ".txt"}

    def _snapshot() -> dict[str, float]:
        """Get modification times for all watched source files."""
        snap = {}
        for d in watch_dirs:
            if not d.exists():
                continue
            for f in d.rglob("*"):
                if f.is_file() and f.suffix in extensions:
                    try:
                        snap[str(f)] = f.stat().st_mtime
                    except OSError:
                        pass
        return snap

    Logger.info(f"👀 Watch mode active (preset: {preset}, interval: {interval}s)")
    Logger.info(f"   Watching: {', '.join(str(d.relative_to(PROJECT_ROOT)) for d in watch_dirs if d.exists())}")
    Logger.info("   Press Ctrl+C to stop.\n")

    prev = _snapshot()
    try:
        while True:
            time.sleep(interval)
            curr = _snapshot()
            changed = []
            for path, mtime in curr.items():
                if path not in prev or prev[path] != mtime:
                    changed.append(path)
            for path in prev:
                if path not in curr:
                    changed.append(path)  # deleted

            if changed:
                Logger.info(f"🔄 {len(changed)} file(s) changed:")
                for c in changed[:5]:
                    from pathlib import Path as _P
                    Logger.info(f"   {_P(c).relative_to(PROJECT_ROOT)}")
                if len(changed) > 5:
                    Logger.info(f"   ... and {len(changed) - 5} more")

                Logger.info(f"   Rebuilding with preset: {preset}")
                rc = run_proc(
                    ["cmake", "--build", "--preset", preset],
                    check=False,
                )
                if rc == 0:
                    Logger.success("✅ Build succeeded")
                else:
                    Logger.error(f"❌ Build failed (exit code {rc})")
                prev = _snapshot()  # re-snapshot after build
            else:
                prev = curr
    except KeyboardInterrupt:
        Logger.info("\n👋 Watch mode stopped.")


def cmd_watch(args: argparse.Namespace) -> CLIResult:
    if GlobalConfig.DRY_RUN:
        Logger.info("[DRY-RUN] Would start watch mode")
        return CLIResult(success=True, message="[DRY-RUN] watch skipped")
    try:
        _impl_cmd_watch(args)
        return CLIResult(success=True, message="Watch mode stopped.")
    except SystemExit as e:
        return CLIResult(success=(e.code == 0), code=e.code or 1, message="Watch failed.")


def cmd_diagnose(args: argparse.Namespace) -> CLIResult:
    """Analyse a build log and print human-friendly diagnostics."""
    from .diagnostics import analyse_output, format_diagnostics

    logfile = getattr(args, "logfile", None)
    if logfile:
        from pathlib import Path
        p = Path(logfile)
        if not p.exists():
            return CLIResult(success=False, code=1, message=f"File not found: {logfile}")
        text = p.read_text(encoding="utf-8", errors="replace")
    else:
        Logger.info("Reading build output from stdin (Ctrl+D to end)...")
        text = sys.stdin.read()

    diags = analyse_output(text)
    if not diags:
        Logger.info("No actionable diagnostics found.")
        return CLIResult(success=True, message="No diagnostics.")

    output = format_diagnostics(diags)
    print(output)
    return CLIResult(success=True, message=f"{len(diags)} diagnostic(s) found.")
