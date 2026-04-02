"""Project-wide utility subcommands: config, doctor, checks, upgrades, clangd."""
from __future__ import annotations

import re
import sys

from core.utils.common import Logger, PROJECT_ROOT, run_proc, GlobalConfig
from core.utils.command_utils import wrap_command
from ._helpers import load_presets


# ── Config commands ───────────────────────────────────────────────────────────

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


# ── Test ──────────────────────────────────────────────────────────────────────

def _impl_cmd_test_run(args) -> None:
    target = getattr(args, "target", None)
    preset = getattr(args, "preset", None) or "gcc-debug-static-x86_64"
    if target:
        # Accept both library names (dummy_lib) and full target names (dummy_lib_tests)
        if not target.endswith("_tests") and not target.startswith("test_"):
            target = target + "_tests"
        run_proc(["cmake", "--build", "--preset", preset, "--target", target])
    else:
        run_proc(["ctest", "--preset", preset, "--output-on-failure"])


# ── Upgrade std ───────────────────────────────────────────────────────────────

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


# ── CI Simulation ─────────────────────────────────────────────────────────────

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
            run_proc([sys.executable, str(PROJECT_ROOT / "scripts" / "tool.py"), "build", "check", "--preset", pname, "--no-sync"])
        except SystemExit as e:
            if e.code != 0:
                print(f"❌ CI failed for preset: {pname}")
                if fail_fast:
                    raise
            continue
    print("\n✅ CI simulation finished")


# ── Check extra (ruff, mypy, cppcheck) ────────────────────────────────────────

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


# ── Init skeleton ─────────────────────────────────────────────────────────────

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

    from core.generator.engine import resolve_project_metadata

    author, contact = resolve_project_metadata({"author": "", "contact": ""})

    # Root context
    ctx = {
        "project_name": name,
        "version": version,
        "description": "Professional Modern C++ / CMake Project Template",
        "author": author,
        "contact": contact,
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


# ── Doctor ────────────────────────────────────────────────────────────────────

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


# ── CMake version ─────────────────────────────────────────────────────────────

def _impl_cmd_cmake_version(args) -> None:
    import subprocess as _sp

    action = getattr(args, "cmake_action", "detect")
    dry    = getattr(args, "dry_run", False)

    if action == "detect":
        r = _sp.run(["cmake", "--version"], capture_output=True, text=True)
        installed_line = r.stdout.strip().split("\n")[0] if r.returncode == 0 else "Unknown"

        root_cmake = PROJECT_ROOT / "CMakeLists.txt"
        min_required = "Unknown"
        if root_cmake.exists():
            for line in root_cmake.read_text(encoding="utf-8").splitlines():
                m = re.search(r'cmake_minimum_required\s*\(\s*VERSION\s+([\d.]+)',
                              line, re.IGNORECASE)
                if m:
                    min_required = m.group(1)
                    break

        print(f"CMake installed : {installed_line}")
        print(f"Project minimum : {min_required}")

    elif action == "set":
        version = getattr(args, "version")
        if not re.match(r'^\d+\.\d+(\.\d+)?$', version):
            print(f"Invalid version format '{version}'. Use MAJOR.MINOR or MAJOR.MINOR.PATCH "
                  "(e.g. '3.25' or '3.28.0')")
            return

        files = list(PROJECT_ROOT.rglob("CMakeLists.txt"))
        changed = 0
        for cm in files:
            rel = cm.relative_to(PROJECT_ROOT)
            # Skip generated / vendored directories
            if any(part in ("external", "build", "_deps", "build-extreme")
                   for part in rel.parts):
                continue
            content = cm.read_text(encoding="utf-8")
            new_content = re.sub(
                r'cmake_minimum_required\s*\(\s*VERSION\s+[\d.]+',
                f'cmake_minimum_required(VERSION {version}',
                content,
                flags=re.IGNORECASE,
            )
            if new_content != content:
                if dry:
                    print(f"[dry-run] Would update {rel} → VERSION {version}")
                else:
                    cm.write_text(new_content, encoding="utf-8")
                    print(f"✅ Updated {rel} → VERSION {version}")
                changed += 1

        prefix = "[dry-run] " if dry else ""
        suffix = "would be " if dry else ""
        print(f"{prefix}{changed} file(s) {suffix}updated.")
    else:
        print(f"Unknown action '{action}'. Use 'detect' or 'set'.")


# ── Clangd ────────────────────────────────────────────────────────────────────

def _impl_cmd_clangd(args) -> None:
    dry = getattr(args, "dry_run", False)

    # Locate compile_commands.json (prefer build/ symlink, then preset dirs)
    compile_db: "Path | None" = None
    for candidate in [
        PROJECT_ROOT / "compile_commands.json",
        PROJECT_ROOT / "build" / "compile_commands.json",
    ]:
        if candidate.exists():
            compile_db = candidate
            break

    # Also search the most-recently-modified preset build dir
    if compile_db is None:
        from pathlib import Path
        build_root = PROJECT_ROOT / "build"
        preset_dirs = sorted(
            (d for d in build_root.iterdir()
             if d.is_dir() and (d / "compile_commands.json").exists()),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if preset_dirs:
            compile_db = preset_dirs[0] / "compile_commands.json"

    if compile_db:
        db_dir = str(compile_db.parent)
    else:
        db_dir = str(PROJECT_ROOT / "build")
        print("Warning: compile_commands.json not found. "
              "Run 'tool build' first, then re-run 'tool sol clangd'.")

    clangd_content = (
        "# .clangd — generated by: python3 scripts/tool.py sol clangd\n"
        "# Regenerate at any time; the file is safe to commit.\n"
        "\n"
        "CompileFlags:\n"
        f"  CompilationDatabase: {db_dir}\n"
        "  Add: [-Wno-unknown-warning-option]\n"
        "\n"
        "InlayHints:\n"
        "  Enabled: Yes\n"
        "  ParameterNames: Yes\n"
        "  DeducedTypes: Yes\n"
        "  BlockEnd: No\n"
        "\n"
        "Diagnostics:\n"
        "  UnusedIncludes: Strict\n"
        "  ClangTidy:\n"
        "    Add:\n"
        "      - modernize*\n"
        "      - performance*\n"
        "      - readability*\n"
        "    Remove:\n"
        "      - readability-magic-numbers\n"
        "      - modernize-use-trailing-return-type\n"
    )

    out_path = PROJECT_ROOT / ".clangd"
    if dry:
        print(f"[dry-run] Would write {out_path}:")
        print(clangd_content)
        return

    out_path.write_text(clangd_content, encoding="utf-8")
    print(f"✅ Written: {out_path}")
    print(f"   CompilationDatabase: {db_dir}")


# ── Wrapper functions ─────────────────────────────────────────────────────────

def cmd_config_get(args):
    return wrap_command(_impl_cmd_config_get, args)


def cmd_config_set(args):
    return wrap_command(_impl_cmd_config_set, args)


def cmd_doctor(args):
    return wrap_command(_impl_cmd_doctor, args)


def cmd_test_run(args):
    return wrap_command(_impl_cmd_test_run, args)


def cmd_upgrade_std(args):
    return wrap_command(_impl_cmd_upgrade_std, args)


def cmd_check_extra(args):
    return wrap_command(_impl_cmd_check_extra, args)


def cmd_init_skeleton(args):
    return wrap_command(_impl_cmd_init_skeleton, args)


def cmd_ci(args):
    return wrap_command(_impl_cmd_ci, args)


def cmd_cmake_version(args):
    return wrap_command(_impl_cmd_cmake_version, args)


def cmd_clangd(args):
    return wrap_command(_impl_cmd_clangd, args)
