"""
core/commands/diagnostics.py — Human-friendly error diagnostics
================================================================

Parses CMake and compiler error output and provides Rust-style
diagnostics with suggested fixes.

Usage:
  tool diagnostics [--log FILE]   # parse build log for known errors
  tool diagnostics --check        # run a quick build and diagnose
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from core.utils.common import Logger, CLIResult, PROJECT_ROOT

COMMAND_META = {
    "name": "diagnostics",
    "description": "Human-friendly build error diagnostics with suggested fixes",
}

# ---------------------------------------------------------------------------
# Known error patterns → friendly messages + suggested fixes
# ---------------------------------------------------------------------------

_PATTERNS: list[tuple[re.Pattern, str, str]] = [
    # CMake: unknown command
    (
        re.compile(r'Unknown CMake command "(\w+)"', re.IGNORECASE),
        'CMake does not know the command "{0}".',
        "Ensure the module defining this function is included via include() "
        "before it is called. Check cmake/ for the module file.",
    ),
    # CMake: could not find package
    (
        re.compile(r"Could not find.*package.*?['\"]?(\w[\w-]+)", re.IGNORECASE),
        'CMake could not find the package "{0}".',
        "Install it via: python3 scripts/tool.py lib deps <lib> --add <pkg>\n"
        "  Or add it to vcpkg.json / conanfile.py.",
    ),
    # CMake: minimum version
    (
        re.compile(r"CMake (\d+\.\d+) or higher is required", re.IGNORECASE),
        "This project requires CMake {0} or higher.",
        "Upgrade CMake: pip install --upgrade cmake\n"
        "  Or: sudo apt install cmake (may need a PPA for newer versions).",
    ),
    # Linker: undefined reference
    (
        re.compile(r"undefined reference to [`']?(\w[\w:]*)", re.IGNORECASE),
        'Linker error: undefined reference to "{0}".',
        "Ensure the library providing this symbol is linked.\n"
        "  Check target_link_libraries() in your CMakeLists.txt.",
    ),
    # Compiler: no such file or directory (include)
    (
        re.compile(r"fatal error: (.+?): No such file or directory"),
        'Missing header: "{0}".',
        "Install the development package or check include paths.\n"
        "  Also verify target_include_directories() in CMakeLists.txt.",
    ),
    # Compiler: no member named
    (
        re.compile(r"no member named '(\w+)' in '([\w:]+)'"),
        "'{1}' has no member named '{0}'.",
        "Check the API documentation for the correct member name.\n"
        "  You may need a newer version of the library or a different C++ standard.",
    ),
    # Ninja: no rule to make target
    (
        re.compile(r"No rule to make target '(.+?)'"),
        'Build system cannot find target "{0}".',
        "Run: cmake --preset <preset> to reconfigure.\n"
        "  The source file may have been renamed or removed.",
    ),
    # Permission denied
    (
        re.compile(r"Permission denied", re.IGNORECASE),
        "Permission denied during build.",
        "Check file permissions in the build directory.\n"
        "  Try: python3 scripts/tool.py build clean && python3 scripts/tool.py build",
    ),
    # Out of memory
    (
        re.compile(r"(out of memory|cannot allocate memory)", re.IGNORECASE),
        "Build ran out of memory.",
        "Reduce parallel jobs: cmake --build --preset <preset> -j 1\n"
        "  Or close other applications to free memory.",
    ),
    # Preset not found
    (
        re.compile(r'Could not find a preset named "(.+?)"'),
        'CMake preset "{0}" not found.',
        "List available presets: python3 scripts/tool.py sol preset list\n"
        "  Or regenerate: python3 scripts/tool.py generate",
    ),
]


def diagnose_output(text: str) -> list[dict[str, str]]:
    """Parse build output and return structured diagnostics.

    Returns list of dicts with keys: error, explanation, suggestion.
    """
    results = []
    seen = set()

    for pattern, explanation_tpl, suggestion in _PATTERNS:
        for match in pattern.finditer(text):
            groups = match.groups()
            explanation = explanation_tpl.format(*groups) if groups else explanation_tpl
            key = (pattern.pattern, groups)
            if key in seen:
                continue
            seen.add(key)
            results.append({
                "error": match.group(0),
                "explanation": explanation,
                "suggestion": suggestion,
            })

    return results


def _format_diagnostic(diag: dict[str, str], index: int) -> str:
    """Format a single diagnostic in Rust-style output."""
    lines = []
    lines.append(f"  \033[91merror[E{index:04d}]\033[0m: {diag['explanation']}")
    lines.append(f"    \033[94m-->\033[0m {diag['error']}")
    lines.append(f"    \033[92m= help:\033[0m {diag['suggestion']}")
    return "\n".join(lines)


def main(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(
        prog="tool diagnostics",
        description="Human-friendly build error diagnostics",
    )
    parser.add_argument(
        "--log", default=None,
        help="Build log file to analyze (default: build_logs/tool.log)",
    )
    parser.add_argument(
        "--check", action="store_true",
        help="Run a quick build and diagnose any errors",
    )
    args = parser.parse_args(argv)

    if args.check:
        import subprocess
        from core.utils.common import run_proc
        Logger.info("Running quick build to capture errors...")
        proc = subprocess.run(
            ["cmake", "--build", "--preset",
             "gcc-debug-static-x86_64", "-j", "1"],
            capture_output=True, text=True, cwd=PROJECT_ROOT,
        )
        text = proc.stdout + "\n" + proc.stderr
    elif args.log:
        text = Path(args.log).read_text(encoding="utf-8")
    else:
        log_file = PROJECT_ROOT / "build_logs" / "tool.log"
        if log_file.exists():
            text = log_file.read_text(encoding="utf-8")
        else:
            Logger.info("No build log found. Run: tool build first, or use --log <file>")
            return

    diagnostics = diagnose_output(text)

    if not diagnostics:
        Logger.success("No known error patterns detected.")
        return

    print(f"\n  Found {len(diagnostics)} diagnostic(s):\n")
    for i, diag in enumerate(diagnostics, 1):
        print(_format_diagnostic(diag, i))
        print()
