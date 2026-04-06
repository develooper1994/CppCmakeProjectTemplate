"""
core/commands/adopt.py — ``tool adopt`` — adopt an existing C++ directory.

Like ``cargo init``: run inside an existing directory containing C++ files,
auto-detect sources, generate ``tool.toml`` + CMake scaffolding around them.

Usage::

    cd my-existing-project
    tool adopt                    # interactive — auto-detect and confirm
    tool adopt --non-interactive  # CI-friendly — accept all detected defaults
    tool adopt --name MyProject   # override project name
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from core.utils.common import Logger

# ---------------------------------------------------------------------------
# Source detection
# ---------------------------------------------------------------------------

_CPP_SRC_EXTS = {".cpp", ".cc", ".cxx", ".c++", ".C"}
_CPP_HDR_EXTS = {".h", ".hpp", ".hxx", ".h++", ".hh"}
_ALL_CPP_EXTS = _CPP_SRC_EXTS | _CPP_HDR_EXTS

_SKIP_DIRS = {
    "build", ".git", ".svn", "node_modules", "__pycache__",
    ".vscode", ".idea", "external", "_deps", ".tool",
    "cmake-build-debug", "cmake-build-release", "out",
}


def _scan_cpp_files(root: Path) -> dict[str, list[Path]]:
    """Walk *root*, return {"headers": [...], "sources": [...]}."""
    headers: list[Path] = []
    sources: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        for fname in filenames:
            ext = Path(fname).suffix.lower()
            full = Path(dirpath) / fname
            rel = full.relative_to(root)
            if ext in _CPP_HDR_EXTS:
                headers.append(rel)
            elif ext in _CPP_SRC_EXTS:
                sources.append(rel)
    return {"headers": sorted(headers), "sources": sorted(sources)}


def _has_main(src: Path, root: Path) -> bool:
    """Quick heuristic: does the source file contain a main() function?"""
    try:
        text = (root / src).read_text(encoding="utf-8", errors="replace")
        return "int main(" in text or "int main (" in text
    except OSError:
        return False


def _infer_libs_and_apps(
    files: dict[str, list[Path]], root: Path
) -> tuple[list[str], list[str]]:
    """Heuristic detection of library and app targets."""
    apps: list[str] = []
    lib_dirs: set[str] = set()

    for src in files["sources"]:
        if _has_main(src, root):
            apps.append(src.stem)
        else:
            # Group by top-level directory or filename
            parts = src.parts
            if len(parts) > 1:
                lib_dirs.add(parts[0])
            else:
                lib_dirs.add(src.stem)

    libs = sorted(lib_dirs - set(apps))
    return libs, apps


def _infer_project_name(root: Path) -> str:
    """Use directory name as project name."""
    name = root.name
    # Clean up common suffixes
    for suffix in ("-src", "-cpp", "-project", "_src", "_cpp"):
        if name.lower().endswith(suffix):
            name = name[: -len(suffix)]
    return name or "MyProject"


# ---------------------------------------------------------------------------
# Config + generation
# ---------------------------------------------------------------------------


def _build_config(
    name: str,
    libs: list[str],
    apps: list[str],
    root: Path,
) -> dict:
    """Build a tool.toml-compatible config dict from detected items."""
    cfg: dict = {
        "project": {
            "name": name,
            "version": "0.1.0",
            "description": f"{name} — initialized with tool rename",
        },
        "generate": {
            "profile": "full" if (libs and apps) else ("library" if libs else "app"),
        },
    }

    if libs:
        lib_section: dict = {}
        for lib_name in libs:
            lib_section[lib_name] = {"type": "normal"}
        cfg["lib"] = lib_section

    if apps:
        app_section: dict = {}
        for app_name in apps:
            dep_list = libs[:] if libs else []
            app_section[app_name] = {"deps": dep_list}
        cfg["app"] = app_section

    return cfg


def _write_tool_toml(root: Path, cfg: dict) -> Path:
    """Write tool.toml from config dict."""
    import tomli_w
    target = root / "tool.toml"
    target.write_text(
        tomli_w.dumps(cfg),
        encoding="utf-8",
    )
    return target


def _write_tool_toml_fallback(root: Path, cfg: dict) -> Path:
    """Write tool.toml without tomli_w (manual TOML serialization)."""
    lines: list[str] = []

    def _write_table(prefix: str, d: dict) -> None:
        for key, val in d.items():
            if isinstance(val, dict):
                lines.append(f"\n[{prefix}.{key}]" if prefix else f"\n[{key}]")
                _write_table(f"{prefix}.{key}" if prefix else key, val)
            elif isinstance(val, list):
                items = ", ".join(f'"{v}"' for v in val)
                lines.append(f'{key} = [{items}]')
            elif isinstance(val, bool):
                lines.append(f'{key} = {"true" if val else "false"}')
            elif isinstance(val, (int, float)):
                lines.append(f'{key} = {val}')
            else:
                lines.append(f'{key} = "{val}"')

    _write_table("", cfg)
    target = root / "tool.toml"
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="tool adopt",
        description="Adopt an existing C++ directory — generate tool.toml + CMake.",
    )
    parser.add_argument(
        "--name", "-n",
        default=None,
        help="Project name (default: directory name).",
    )
    parser.add_argument(
        "--target-dir", "-t",
        type=Path,
        default=None,
        help="Directory to initialize (default: current directory).",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        default=False,
        help="Accept all detected defaults without prompting.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        default=False,
        help="Overwrite existing tool.toml if present.",
    )
    args = parser.parse_args(argv)

    root = (args.target_dir or Path.cwd()).resolve()
    if not root.is_dir():
        Logger.error(f"Not a directory: {root}")
        sys.exit(1)

    # Check for existing tool.toml
    existing_toml = root / "tool.toml"
    if existing_toml.exists() and not args.force:
        Logger.error(f"tool.toml already exists at {root}. Use --force to overwrite.")
        sys.exit(1)

    Logger.info(f"Scanning {root} for C++ sources...")
    files = _scan_cpp_files(root)
    n_headers = len(files["headers"])
    n_sources = len(files["sources"])
    Logger.info(f"  Found {n_headers} header(s), {n_sources} source file(s)")

    if n_headers == 0 and n_sources == 0:
        Logger.warn("No C++ files detected. Generating a minimal template.")

    libs, apps = _infer_libs_and_apps(files, root)
    name = args.name or _infer_project_name(root)

    Logger.info(f"  Project name: {name}")
    if libs:
        Logger.info(f"  Detected libraries: {', '.join(libs)}")
    if apps:
        Logger.info(f"  Detected apps (files with main()): {', '.join(apps)}")

    if not args.non_interactive and sys.stdin.isatty():
        print()
        answer = input(f"Initialize '{name}' with {len(libs)} lib(s), {len(apps)} app(s)? [Y/n] ").strip()
        if answer.lower() in ("n", "no"):
            Logger.info("Aborted.")
            return

    cfg = _build_config(name, libs, apps, root)

    # Write tool.toml
    try:
        toml_path = _write_tool_toml(root, cfg)
    except ImportError:
        toml_path = _write_tool_toml_fallback(root, cfg)
    Logger.success(f"  Created {toml_path.relative_to(root)}")

    # Generate CMake scaffolding
    from core.generator.engine import generate
    from core.generator.merge import ConflictPolicy

    policy = ConflictPolicy.OVERWRITE if args.force else ConflictPolicy.SKIP
    result = generate(
        target_dir=root,
        policy=policy,
        config=cfg,
    )

    for f in result.created:
        Logger.success(f"  + {f}")
    for f in result.written:
        Logger.info(f"  ~ {f}")
    for f in result.skipped:
        Logger.info(f"  = {f} (kept existing)")
    for f in result.errors:
        Logger.error(f"  ✗ {f}")

    Logger.info(f"Done: {result.summary()}")
    Logger.info("Next steps:")
    Logger.info("  1. Review tool.toml and adjust as needed")
    Logger.info("  2. Move your sources into the generated directory structure")
    Logger.info("  3. Run: python3 scripts/tool.py build")

    if result.errors:
        sys.exit(1)
