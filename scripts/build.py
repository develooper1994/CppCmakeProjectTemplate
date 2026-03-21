#!/usr/bin/env python3
"""
build.py — Unified project automation tool.

Subcommands:
    build      [--preset X]                    Configure + compile
    check      [--preset X] [--no-sync]        Build + test + extension sync
    clean      [--all]                          Remove build artifacts
    deploy     --host user@host [--path /tmp]   Remote deploy via rsync
               [--preset X]
    extension  [--install]                      Build .vsix extension package

Usage:
    python3 scripts/build.py                   # → build (default preset)
    python3 scripts/build.py build --preset clang-debug-static-x86_64
    python3 scripts/build.py check
    python3 scripts/build.py check --no-sync
    python3 scripts/build.py clean
    python3 scripts/build.py clean --all
    python3 scripts/build.py deploy --host user@192.168.1.10
    python3 scripts/build.py extension
    python3 scripts/build.py extension --install
"""

from __future__ import annotations

import argparse
import json
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_DIR      = PROJECT_ROOT / "build_logs"
EXT_DIR      = PROJECT_ROOT / "scripts" / "extension"
TEMPLATE_DIR = EXT_DIR / "templates"

DEFAULT_PRESET: dict[str, str] = {
    "Linux":   "gcc-debug-static-x86_64",
    "Windows": "msvc-debug-static-x64",
    "Darwin":  "clang-debug-static-x86_64",
}

# Files/dirs included in the extension template bundle
EXT_INCLUDE: list[str] = [
    "CMakeLists.txt", "CMakePresets.json", "conanfile.py", "vcpkg.json",
    "Dockerfile", ".dockerignore", ".gitignore", ".geminiignore", ".clang-format",
    "LICENSE", "README.md", "AGENTS.md", "GEMINI.md", "MASTER_GENERATOR_PROMPT.md",
    "cmake", "apps", "libs", "tests", "scripts", "docs", "external",
    ".github", ".cursor",
]

# Paths excluded from extension template (relative to project root, forward-slash)
EXT_EXCLUDE: set[str] = {
    "build", "build_logs", "__pycache__", ".cache", "coverage_report",
    "scripts/extension",           # circular
    "scripts/build.py",            # dev-only
    "scripts/toollib.py",          # dev-only
    "scripts/toolsolution.py",      # dev-only
    "scripts/common.py",            # dev-only
    "scripts/setup_hooks.py",      # dev-only
    "İstekler-Eksikler-Sorunlar.md",
}

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def default_preset() -> str:
    return DEFAULT_PRESET.get(platform.system(), "gcc-debug-static-x86_64")


def run(cmd: list[str], *, cwd: Path = PROJECT_ROOT, log: Path | None = None) -> None:
    print(f"  --> {' '.join(cmd)}")
    if log:
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("w", encoding="utf-8") as f:
            result = subprocess.run(
                cmd, cwd=cwd,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            )
            f.write(result.stdout)
            print(result.stdout, end="")
    else:
        result = subprocess.run(cmd, cwd=cwd)

    if result.returncode != 0:
        msg = f"❌ FAILED (exit {result.returncode})"
        if log:
            msg += f" — log: {log}"
        print(msg, file=sys.stderr)
        sys.exit(result.returncode)


def header(title: str, preset: str | None = None) -> None:
    print("=" * 52)
    print(f"  {title}")
    if preset:
        print(f"  Preset : {preset}")
    print(f"  Root   : {PROJECT_ROOT}")
    print("=" * 52)


# ──────────────────────────────────────────────────────────────────────────────
# build
# ──────────────────────────────────────────────────────────────────────────────

def cmd_build(args: argparse.Namespace) -> None:
    preset = args.preset or default_preset()
    header("Build", preset)

    print(f"\n[1/2] Configure...")
    run(["cmake", "--preset", preset], log=LOG_DIR / "configure.log")
    print("✅ Configure OK")

    print(f"\n[2/2] Build...")
    run(["cmake", "--build", "--preset", preset], log=LOG_DIR / "build.log")
    print(f"\n✅ Build complete.")


# ──────────────────────────────────────────────────────────────────────────────
# check  (build + test + extension sync)
# ──────────────────────────────────────────────────────────────────────────────

def cmd_check(args: argparse.Namespace) -> None:
    preset = args.preset or default_preset()
    steps  = 4 if not args.no_sync else 3
    header("Build Check", preset)

    print(f"\n[1/{steps}] Configure...")
    run(["cmake", "--preset", preset], log=LOG_DIR / "configure.log")
    print("✅ Configure OK")

    print(f"\n[2/{steps}] Build...")
    run(["cmake", "--build", "--preset", preset], log=LOG_DIR / "build.log")
    print("✅ Build OK")

    print(f"\n[3/{steps}] Test...")
    run(["ctest", "--preset", preset, "--output-on-failure"], log=LOG_DIR / "test.log")
    print("✅ Tests OK")

    if not args.no_sync:
        print(f"\n[4/{steps}] Extension sync...")
        _do_extension(install=False, log=LOG_DIR / "extension.log")
        print("✅ Extension OK")

    print("\n" + "=" * 52)
    print("✅ All steps passed!")
    print(f"   Logs: {LOG_DIR}/")
    print("=" * 52)


# ──────────────────────────────────────────────────────────────────────────────
# clean
# ──────────────────────────────────────────────────────────────────────────────

def cmd_clean(args: argparse.Namespace) -> None:
    targets = ["build", ".cache", "coverage_report", "build_logs"]
    if args.all:
        targets += [str(f) for f in PROJECT_ROOT.glob("*.vsix")]

    print("--> Cleaning...")
    for d in targets:
        p = PROJECT_ROOT / d
        if p.exists():
            print(f"    Removing: {d}")
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()
        else:
            print(f"    Skip: {d} (not found)")
    print("✅ Clean done.")


# ──────────────────────────────────────────────────────────────────────────────
# deploy
# ──────────────────────────────────────────────────────────────────────────────

def cmd_deploy(args: argparse.Namespace) -> None:
    preset     = args.preset or default_preset()
    source_dir = PROJECT_ROOT / "build" / preset

    if not source_dir.exists():
        print(f"❌ Build directory not found: {source_dir}", file=sys.stderr)
        print("   Run: python3 scripts/build.py build", file=sys.stderr)
        sys.exit(1)

    print(f"--> Deploying {preset} → {args.host}:{args.path}")
    for folder in ["apps", "libs"]:
        p = source_dir / folder
        if p.exists():
            print(f"    Syncing {folder}/...")
            run(["rsync", "-avz", "--delete", str(p) + "/", f"{args.host}:{args.path}/{folder}/"])
    print("✅ Deploy complete.")


# ──────────────────────────────────────────────────────────────────────────────
# extension  (build .vsix)
# ──────────────────────────────────────────────────────────────────────────────

def _is_excluded(rel: str) -> bool:
    rel = rel.replace("\\", "/")
    return any(rel == ex or rel.startswith(ex + "/") for ex in EXT_EXCLUDE)


def _sync_templates() -> int:
    if TEMPLATE_DIR.exists():
        shutil.rmtree(TEMPLATE_DIR)
    TEMPLATE_DIR.mkdir(parents=True)
    count = 0
    for entry in EXT_INCLUDE:
        src = PROJECT_ROOT / entry
        if not src.exists():
            print(f"  [WARN] Not found, skipped: {entry}")
            continue
        pairs = (
            [(src, entry)]
            if src.is_file()
            else [
                (p, str(Path(entry) / p.relative_to(src)).replace("\\", "/"))
                for p in src.rglob("*") if p.is_file()
            ]
        )
        for abs_src, rel in pairs:
            if _is_excluded(rel):
                continue
            dst = TEMPLATE_DIR / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(abs_src, dst)
            count += 1
    return count


def _sync_version() -> None:
    """Sync version from CMakeLists.txt (or git tag fallback) → extension package.json."""
    sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
    try:
        from common import get_project_version
        version = get_project_version(PROJECT_ROOT)
    except ImportError:
        # fallback inline if common.py not available
        clean = re.sub(r'#.*', '', (PROJECT_ROOT / "CMakeLists.txt").read_text())
        m = re.search(r'project\s*\([^)]*VERSION\s+([\d.]+)', clean, re.IGNORECASE | re.DOTALL)
        version = m.group(1) if m else "0.0.0"

    pkg_path = EXT_DIR / "package.json"
    if not pkg_path.exists():
        print("  ❌ package.json not found!"); return

    pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
    if pkg.get("version") != version:
        pkg["version"] = version
        pkg_path.write_text(json.dumps(pkg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"  ✅ Version synced: {version}")
    else:
        print(f"  ⏭  Version up-to-date: {version}")
def _sync_license() -> None:
    src = PROJECT_ROOT / "LICENSE"
    if src.exists():
        shutil.copy2(src, EXT_DIR / "LICENSE")
        print("  ✅ LICENSE copied")


def _do_extension(install: bool, publish: bool = False, log: Path | None = None) -> None:
    _sync_version()
    _sync_license()

    count = _sync_templates()
    print(f"  ✅ {count} files → templates/")

    # Remove old .vsix from extension dir
    for f in EXT_DIR.glob("*.vsix"):
        f.unlink()
        print(f"  🗑  Removed: {f.name}")

    run(["npm", "install"], cwd=EXT_DIR, log=None)
    # Output .vsix into scripts/extension/ (not project root)
    run(["npx", "vsce", "package", "--out", str(EXT_DIR)], cwd=EXT_DIR, log=log)

    vsix_files = sorted(EXT_DIR.glob("*.vsix"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not vsix_files:
        print("❌ .vsix not produced.", file=sys.stderr)
        sys.exit(1)
    vsix = vsix_files[0]
    print(f"  ✅ Package: scripts/extension/{vsix.name}")

    if install:
        run(["code", "--install-extension", str(vsix)], cwd=PROJECT_ROOT)
        print("  ✅ Installed. Restart VS Code.")

    if publish:
        print("\n  Publishing to VS Code Marketplace...")
        run(["npx", "vsce", "publish"], cwd=EXT_DIR)
        print("  ✅ Published.")


def cmd_extension(args: argparse.Namespace) -> None:
    header("Extension Build")
    print()
    _do_extension(install=args.install, publish=getattr(args, "publish", False))


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="build.py",
        description="Unified project automation (build / check / clean / deploy / extension)",
    )
    sub = parser.add_subparsers(dest="command")

    # build (also the default when no subcommand)
    p = sub.add_parser("build", help="Configure + compile")
    p.add_argument("--preset", default=None, help=f"CMake preset (default: auto-detect)")
    p.set_defaults(func=cmd_build)

    # check
    p = sub.add_parser("check", help="Build + test + extension sync")
    p.add_argument("--preset",   default=None)
    p.add_argument("--no-sync",  action="store_true", help="Skip extension step")
    p.set_defaults(func=cmd_check)

    # clean
    p = sub.add_parser("clean", help="Remove build artifacts")
    p.add_argument("--all", action="store_true", help="Also remove .vsix files and build_logs")
    p.set_defaults(func=cmd_clean)

    # deploy
    p = sub.add_parser("deploy", help="Remote deploy via rsync")
    p.add_argument("--host",   required=True, help="user@host")
    p.add_argument("--path",   default="/tmp/cpp_project", help="Remote path")
    p.add_argument("--preset", default=None)
    p.set_defaults(func=cmd_deploy)

    # extension
    p = sub.add_parser("extension", help="Build .vsix extension package")
    p.add_argument("--install", action="store_true", help="Install into VS Code after build")
    p.add_argument("--publish", action="store_true", help="Publish to VS Code Marketplace after build")
    p.set_defaults(func=cmd_extension)

    return parser


def main() -> None:
    parser = build_parser()
    args   = parser.parse_args()

    # Default: build
    if args.command is None:
        args = parser.parse_args(["build"])

    args.func(args)


if __name__ == "__main__":
    main()
