#!/usr/bin/env python3
"""
plugins/setup.py — Dependency checker/installer plugin.

Usage: tool setup [--install] [--do-install] [--all] [--check] [--category CAT]
                  [--env [DIR]] [--install-env] [--recreate]

  --install      Show the install command (informational)
  --do-install   Actually run 'sudo apt install ...' / 'brew install ...' to install
  --all          Include optional packages in the check/install
  --check        Check all dependencies and report status (no install)
  --category CAT Only check/install a specific category
  --env [DIR]    Create/activate a Python venv (default dir: .venv)
  --install-env  Install requirements-dev.txt into the venv
  --recreate     Recreate venv if it already exists
"""
from __future__ import annotations

import argparse
import importlib
import platform
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from core.utils.common import (
    Logger,
    PROJECT_ROOT,
    find_missing_binaries,
    create_venv,
    install_python_requirements,
    print_venv_activation,
)

PLUGIN_META = {
    "name": "setup",
    "description": "Check and optionally install system and Python dependencies for the project.",
}

# ── Dependency Categories ─────────────────────────────────────────────────────
# Each category: { binary_name: package_name }
# Categories are ordered by importance.

DEPENDENCY_CATEGORIES: dict[str, dict[str, str | dict]] = {
    "critical_build": {
        "description": "Essential build tools — project cannot build without these",
        "binaries": {
            "cmake":   "cmake",
            "ninja":   "ninja-build",
            "git":     "git",
            "python3": "python3",
        },
        "required": True,
    },
    "compiler": {
        "description": "C/C++ compilers — at least one is required",
        "binaries": {
            "gcc":   "build-essential",
            "g++":   "build-essential",
            "clang": "clang",
        },
        "required": True,
        "any_of": True,  # at least ONE must be present
    },
    "installer_tools": {
        "description": "Package managers and download tools — needed to install other dependencies",
        "binaries": {
            "pip3":  "python3-pip",
            "curl":  "curl",
            "wget":  "wget",
        },
        "required": False,
    },
    "python_runtime": {
        "description": "Python packages needed by the scripts at runtime",
        "packages": ["jinja2"],  # checked via importlib
        "packages_any": [["tomllib", "tomli"]],  # tomllib (3.11+) or tomli fallback
        "required": True,
    },
    "python_dev": {
        "description": "Python packages for development and testing",
        "packages": ["pytest", "pytest_cov", "ruff"],
        "required": False,
    },
    "optional_tools": {
        "description": "Code quality, formatting, and documentation tools",
        "binaries": {
            "ccache":       "ccache",
            "clang-format": "clang-format",
            "clang-tidy":   "clang-tidy",
            "cppcheck":     "cppcheck",
            "doxygen":      "doxygen",
            "gcovr":        "gcovr",
            "lcov":         "lcov",
            "gitleaks":     "gitleaks",
        },
        "required": False,
    },
    "optional_platform": {
        "description": "Platform-specific debugging, profiling, and container tools",
        "binaries": {
            "valgrind":    "valgrind",
            "perf":        "linux-tools-generic",
            "docker":      "docker.io",
            "osv-scanner": "osv-scanner",
        },
        "required": False,
    },
}

# Legacy aliases for backward compatibility
MANDATORY_SYS = DEPENDENCY_CATEGORIES["critical_build"]["binaries"]
OPTIONAL_SYS = {
    **DEPENDENCY_CATEGORIES["optional_tools"]["binaries"],
    **DEPENDENCY_CATEGORIES["optional_platform"]["binaries"],
}

# ── Package manager mappings ──────────────────────────────────────────────────

_BREW_MAP: dict[str, str] = {
    "cmake":       "cmake",
    "ninja-build": "ninja",
    "git":         "git",
    "python3":     "python",
    "build-essential": "",  # Xcode CLT provides this
    "clang":       "llvm",
    "clang-format": "clang-format",
    "clang-tidy":  "llvm",
    "ccache":      "ccache",
    "cppcheck":    "cppcheck",
    "doxygen":     "doxygen",
    "gcovr":       "gcovr",
    "lcov":        "lcov",
    "valgrind":    "",  # not available on macOS
    "gitleaks":    "gitleaks",
    "python3-pip": "",  # included with python
    "curl":        "curl",
    "wget":        "wget",
}

_WINGET_MAP: dict[str, str] = {
    "cmake":       "Kitware.CMake",
    "ninja-build": "Ninja-build.Ninja",
    "git":         "Git.Git",
    "python3":     "Python.Python.3.12",
    "doxygen":     "DimitriVanHeesch.Doxygen",
    "clang":       "LLVM.LLVM",
    "clang-format": "LLVM.LLVM",
    "clang-tidy":  "LLVM.LLVM",
    "ccache":      "ccache.ccache",
    "cppcheck":    "Cppcheck.Cppcheck",
    "gitleaks":    "Gitleaks.Gitleaks",
}

_CHOCO_MAP: dict[str, str] = {
    "cmake":       "cmake",
    "ninja-build": "ninja",
    "git":         "git",
    "python3":     "python",
    "doxygen":     "doxygen.install",
    "clang":       "llvm",
    "clang-format": "llvm",
    "clang-tidy":  "llvm",
    "ccache":      "ccache",
    "cppcheck":    "cppcheck",
}


def _detect_package_manager() -> str:
    """Return 'apt', 'brew', 'dnf', 'pacman', 'winget', 'choco', or 'unknown'."""
    sys_name = platform.system().lower()
    if sys_name == "darwin":
        if shutil.which("brew"):
            return "brew"
    if sys_name == "windows":
        if shutil.which("winget"):
            return "winget"
        if shutil.which("choco"):
            return "choco"
    for pm in ("apt-get", "dnf", "pacman"):
        if shutil.which(pm):
            return pm.split("-")[0]  # 'apt-get' -> 'apt'
    return "unknown"


def _build_install_cmd(pkg_manager: str, packages: list[str]) -> list[str] | None:
    """Return a ready-to-run install command list, or None if unsupported."""
    if pkg_manager == "apt":
        return ["sudo", "apt-get", "install", "-y"] + packages
    if pkg_manager == "brew":
        brew_pkgs = [_BREW_MAP.get(p, p) for p in packages]
        brew_pkgs = [p for p in brew_pkgs if p]  # remove empty (unavailable on macOS)
        return ["brew", "install"] + list(dict.fromkeys(brew_pkgs))  # deduplicate
    if pkg_manager == "dnf":
        return ["sudo", "dnf", "install", "-y"] + packages
    if pkg_manager == "pacman":
        return ["sudo", "pacman", "-S", "--noconfirm"] + packages
    if pkg_manager == "winget":
        winget_pkgs = [_WINGET_MAP.get(p, p) for p in packages if p in _WINGET_MAP]
        if not winget_pkgs:
            return None
        return ["winget", "install", "--accept-source-agreements", "--accept-package-agreements"] + winget_pkgs
    if pkg_manager == "choco":
        choco_pkgs = [_CHOCO_MAP.get(p, p) for p in packages if p in _CHOCO_MAP]
        if not choco_pkgs:
            return None
        return ["choco", "install", "-y"] + list(dict.fromkeys(choco_pkgs))
    return None


def _get_tool_version(binary: str) -> str | None:
    """Try to get the version string of a binary tool."""
    try:
        result = subprocess.run(
            [binary, "--version"], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            # Take the first line that contains a version-like pattern
            for line in result.stdout.strip().splitlines():
                if any(c.isdigit() for c in line):
                    return line.strip()
        return None
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None


def _check_python_package(module_name: str) -> bool:
    """Check if a Python package is importable."""
    try:
        importlib.import_module(module_name)
        return True
    except ImportError:
        return False


def _check_category(cat_name: str, cat_info: dict, verbose: bool = False) -> dict:
    """Check a single dependency category. Returns a status report dict."""
    desc = cat_info.get("description", "")
    required = cat_info.get("required", False)
    any_of = cat_info.get("any_of", False)
    binaries = cat_info.get("binaries", {})
    packages = cat_info.get("packages", [])

    found = {}
    missing = {}

    # Check binaries
    for bin_name, pkg_name in binaries.items():
        if shutil.which(bin_name):
            version = _get_tool_version(bin_name) if verbose else None
            found[bin_name] = {"package": pkg_name, "version": version}
        else:
            missing[bin_name] = pkg_name

    # Check Python packages
    for pkg in packages:
        if _check_python_package(pkg):
            found[pkg] = {"package": pkg, "version": None, "type": "python"}
        else:
            missing[pkg] = pkg

    # Check packages_any (at least one of group must be importable)
    for group in cat_info.get("packages_any", []):
        group_found = False
        for pkg in group:
            if _check_python_package(pkg):
                found[pkg] = {"package": pkg, "version": None, "type": "python"}
                group_found = True
                break
        if not group_found:
            missing[" or ".join(group)] = group[0]

    # For any_of categories, it's OK if at least one is found
    if any_of and found:
        status = "ok"
    elif missing and required:
        status = "error"
    elif missing:
        status = "warning"
    else:
        status = "ok"

    return {
        "name": cat_name,
        "description": desc,
        "required": required,
        "any_of": any_of,
        "status": status,
        "found": found,
        "missing": missing,
    }


def check_all_dependencies(categories: list[str] | None = None,
                           verbose: bool = False) -> list[dict]:
    """Check dependencies across all (or specified) categories. Returns list of reports."""
    results = []
    for cat_name, cat_info in DEPENDENCY_CATEGORIES.items():
        if categories and cat_name not in categories:
            continue
        results.append(_check_category(cat_name, cat_info, verbose=verbose))
    return results


def print_dependency_report(results: list[dict]) -> int:
    """Print a formatted dependency report. Returns count of critical errors."""
    errors = 0
    for r in results:
        status_icon = {"ok": "✅", "warning": "⚠️ ", "error": "❌"}.get(r["status"], "?")
        any_label = " (at least one)" if r.get("any_of") else ""
        req_label = " [required]" if r["required"] else " [optional]"
        print(f"\n{status_icon} {r['name']}{req_label}{any_label}")
        print(f"   {r['description']}")

        for name, info in r["found"].items():
            ver = f" — {info['version']}" if info.get("version") else ""
            kind = " (python)" if info.get("type") == "python" else ""
            print(f"   ✅ {name}{kind}{ver}")

        for name, pkg in r["missing"].items():
            if r.get("any_of") and r["status"] == "ok":
                print(f"   ⬚  {name} (not installed, but alternative found)")
            elif r["required"]:
                print(f"   ❌ {name} (package: {pkg})")
                errors += 1
            else:
                print(f"   ⚠️  {name} (package: {pkg})")

    return errors


def _parse_version(version_str: str) -> str | None:
    """Extract a version number (X.Y.Z or X.Y) from a version string."""
    import re
    m = re.search(r'(\d+\.\d+(?:\.\d+)?)', version_str)
    return m.group(1) if m else None


def detect_environment() -> dict:
    """Auto-detect the build environment: OS, arch, compilers, package manager, features."""
    info: dict = {}

    # OS & Architecture
    info["os"] = platform.system()
    info["os_release"] = platform.release()
    info["arch"] = platform.machine()
    info["python_version"] = platform.python_version()

    # Package manager
    info["package_manager"] = _detect_package_manager()

    # Compilers
    compilers = {}
    for compiler in ["gcc", "g++", "clang", "clang++"]:
        if shutil.which(compiler):
            ver = _get_tool_version(compiler)
            compilers[compiler] = _parse_version(ver) if ver else "found"
    info["compilers"] = compilers

    # CMake version
    cmake_ver = _get_tool_version("cmake")
    info["cmake_version"] = _parse_version(cmake_ver) if cmake_ver else None

    # Build features
    features = {}
    features["ccache"] = shutil.which("ccache") is not None
    features["ninja"] = shutil.which("ninja") is not None
    features["sanitizers"] = any(shutil.which(c) for c in ["clang", "gcc"])
    features["coverage"] = any(shutil.which(t) for t in ["gcovr", "lcov"])
    features["static_analysis"] = any(shutil.which(t) for t in ["clang-tidy", "cppcheck"])
    features["documentation"] = shutil.which("doxygen") is not None
    features["docker"] = shutil.which("docker") is not None
    features["valgrind"] = shutil.which("valgrind") is not None
    features["fuzz_testing"] = shutil.which("clang") is not None  # libFuzzer comes with clang
    info["features"] = features

    return info


def print_environment_report(info: dict) -> None:
    """Print a formatted environment detection report."""
    print("── Platform ──")
    print(f"  OS:              {info['os']} ({info['os_release']})")
    print(f"  Architecture:    {info['arch']}")
    print(f"  Python:          {info['python_version']}")
    print(f"  Package Manager: {info['package_manager']}")
    print(f"  CMake:           {info.get('cmake_version', 'not found')}")

    print("\n── Compilers ──")
    if info["compilers"]:
        for name, ver in info["compilers"].items():
            print(f"  {name:<14} {ver}")
    else:
        print("  ❌ No C/C++ compiler found!")

    print("\n── Available Features ──")
    for feat, available in info["features"].items():
        icon = "✅" if available else "⬚ "
        print(f"  {icon} {feat}")


def main(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(prog="tool setup",
                                     description="Check and install project dependencies.")
    parser.add_argument("--install", action="store_true",
                        help="Show installation command (informational)")
    parser.add_argument("--do-install", action="store_true", dest="do_install",
                        help="Actually run the package manager to install missing packages")
    parser.add_argument("--all", action="store_true",
                        help="Include optional packages in the check/install")
    parser.add_argument("--check", action="store_true",
                        help="Check all dependencies and print a categorized report")
    parser.add_argument("--detect", action="store_true",
                        help="Auto-detect build environment (OS, compilers, features)")
    parser.add_argument("--category", type=str, default=None,
                        choices=list(DEPENDENCY_CATEGORIES.keys()),
                        help="Only check/install a specific dependency category")
    parser.add_argument("--env", nargs="?", const=".venv", default=None,
                        help="Create Python venv (optional dir, default: .venv)")
    parser.add_argument("--install-env", action="store_true", dest="install_env",
                        help="Install requirements-dev.txt into the created venv")
    parser.add_argument("--recreate", action="store_true",
                        help="Recreate venv if it already exists")
    args = parser.parse_args(argv)

    # ── 0a. Environment detection mode ──────────────────────────────────────
    if args.detect:
        info = detect_environment()
        print_environment_report(info)
        return

    # ── 0b. Full dependency check mode ──────────────────────────────────────
    if args.check:
        cats = [args.category] if args.category else None
        results = check_all_dependencies(categories=cats, verbose=True)
        errors = print_dependency_report(results)
        print()
        if errors:
            Logger.error(f"{errors} critical dependency(ies) missing.")
            sys.exit(1)
        else:
            Logger.success("All checked dependencies are satisfied.")
        return
    # ── 1. System Dependencies ──────────────────────────────────────────────
    if args.category:
        cat_info = DEPENDENCY_CATEGORIES.get(args.category)
        if not cat_info:
            Logger.error(f"Unknown category: {args.category}")
            sys.exit(1)
        binaries = cat_info.get("binaries", {})
        deps_to_check = dict(binaries)
    else:
        deps_to_check = dict(MANDATORY_SYS)
        if args.all:
            deps_to_check.update(OPTIONAL_SYS)

    missing = find_missing_binaries(deps_to_check)

    if not missing:
        Logger.success("All system dependencies are installed.")
    else:
        Logger.warn("Missing system dependencies:")
        for bin_name, pkg in missing.items():
            print(f"  - {bin_name:<18} (package: {pkg})")

        pm = _detect_package_manager()
        pkg_list = sorted(set(missing.values()))
        install_cmd = _build_install_cmd(pm, pkg_list)

        if install_cmd is None:
            Logger.warn(f"Unsupported package manager '{pm}'. Install manually:")
            for p in pkg_list:
                print(f"  {p}")
        elif args.do_install:
            Logger.info(f"Running: {shlex.join(install_cmd)}")
            rc = subprocess.run(install_cmd).returncode
            if rc == 0:
                Logger.success("System packages installed successfully.")
            else:
                Logger.error(f"Install failed with exit code {rc}.")
                sys.exit(rc)
        elif args.install:
            print(f"\nInstall command ({pm}):\n  {shlex.join(install_cmd)}")
        else:
            print(f"\nRe-run with --install to see the install command, or --do-install to run it.")

    # ── 2. Python Venv ──────────────────────────────────────────────────────
    if args.env is not None:
        env_path = PROJECT_ROOT / args.env
        py_exe = create_venv(env_path, recreate=args.recreate)
        if args.install_env:
            install_python_requirements(py_exe, PROJECT_ROOT / "requirements-dev.txt")
        print_venv_activation(env_path)
