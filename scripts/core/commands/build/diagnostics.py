"""
core/commands/build/diagnostics.py — Human-friendly error diagnostics.

Parses compiler and CMake error output and provides actionable suggestions,
inspired by Rust's compiler diagnostics.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class Diagnostic:
    """A single diagnostic with source info and a suggestion."""
    file: str
    line: int | None
    message: str
    suggestion: str
    category: str  # "error" | "warning" | "note"


# ---------------------------------------------------------------------------
# Pattern → suggestion rules
# ---------------------------------------------------------------------------

_RULES: list[tuple[re.Pattern, str, str]] = [
    # Undefined reference / linker errors
    (re.compile(r"undefined reference to [`'](.+?)'"),
     "Linker: undefined reference to '{0}'",
     "Check that the library providing '{0}' is linked. "
     "Add target_link_libraries(<target> PRIVATE <library>) in CMakeLists.txt."),

    # Missing header
    (re.compile(r"fatal error: (.+?): No such file or directory"),
     "Missing header: {0}",
     "Install the development package that provides '{0}', "
     "or add the correct include path via target_include_directories()."),

    # No member named
    (re.compile(r"no member named '(.+?)' in '(.+?)'"),
     "No member '{0}' in '{1}'",
     "Check the class/struct definition for '{1}'. The member '{0}' may be "
     "misspelled, or you may need a newer standard (e.g. -std=c++17/20)."),

    # Implicit conversion loses data
    (re.compile(r"implicit conversion loses (integer|floating-point) precision"),
     "Implicit narrowing conversion",
     "Use static_cast<TargetType>(value) to make the conversion explicit."),

    # Unused variable
    (re.compile(r"unused variable '(.+?)'"),
     "Unused variable '{0}'",
     "Remove the variable or prefix with [[maybe_unused]]."),

    # CMake: could not find package
    (re.compile(r"Could not find a package configuration file provided by \"(.+?)\""),
     "CMake: package '{0}' not found",
     "Install '{0}' via your package manager (vcpkg/conan/apt), "
     "or add it to vcpkg.json / conanfile.py."),

    # CMake: minimum version
    (re.compile(r"CMake (\d+\.\d+) or higher is required"),
     "CMake version {0}+ required",
     "Upgrade CMake: pip install --upgrade cmake  (or use your system's package manager)."),

    # Redefinition / multiple definition
    (re.compile(r"multiple definition of [`'](.+?)'"),
     "Multiple definition of '{0}'",
     "Ensure '{0}' is defined in exactly one .cpp file. "
     "Use 'inline' for definitions in headers, or move to a single translation unit."),

    # Template instantiation depth
    (re.compile(r"template instantiation depth exceeds maximum"),
     "Template instantiation depth exceeded",
     "Check for infinite template recursion. "
     "Increase with -ftemplate-depth=N if the recursion is intentional."),

    # Static assertion failed
    (re.compile(r"static assertion failed:?\s*(.*)"),
     "Static assertion failed: {0}",
     "Review the static_assert condition. This is a compile-time check "
     "that a required invariant is not met."),

    # Segfault in compiler (ICE)
    (re.compile(r"internal compiler error|ICE|Please submit a full bug report"),
     "Internal compiler error (ICE)",
     "This is a compiler bug. Try: (1) update your compiler, (2) simplify the code, "
     "(3) compile with a different optimisation level, (4) report the bug upstream."),
]

# GCC/Clang error line: file:line:col: error: message
_LOCATION_RE = re.compile(r"^(.+?):(\d+)(?::\d+)?:\s*(?:error|warning|fatal error):\s*(.+)")


def analyse_output(output: str) -> list[Diagnostic]:
    """Parse build output and return diagnostics with suggestions."""
    diagnostics: list[Diagnostic] = []
    seen: set[str] = set()

    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        loc = _LOCATION_RE.match(line)
        src_file = loc.group(1) if loc else ""
        src_line = int(loc.group(2)) if loc else None
        msg_text = loc.group(3) if loc else line

        for pattern, msg_tmpl, suggestion_tmpl in _RULES:
            m = pattern.search(msg_text) or pattern.search(line)
            if m:
                groups = m.groups()
                msg = msg_tmpl.format(*groups) if groups else msg_tmpl
                suggestion = suggestion_tmpl.format(*groups) if groups else suggestion_tmpl
                key = (src_file, src_line, msg)
                if key not in seen:
                    seen.add(key)
                    category = "error" if "error" in line.lower() else "warning"
                    diagnostics.append(Diagnostic(
                        file=src_file,
                        line=src_line,
                        message=msg,
                        suggestion=suggestion,
                        category=category,
                    ))
                break

    return diagnostics


def format_diagnostics(diagnostics: list[Diagnostic]) -> str:
    """Format diagnostics into a human-readable string."""
    if not diagnostics:
        return ""
    parts = ["\n╭─ Build Diagnostics ─────────────────────────────"]
    for d in diagnostics:
        icon = "✗" if d.category == "error" else "⚠"
        loc = f"  {d.file}:{d.line}" if d.file and d.line else ""
        parts.append(f"│ {icon} {d.message}{loc}")
        parts.append(f"│   ➜ {d.suggestion}")
        parts.append("│")
    parts.append("╰──────────────────────────────────────────────────")
    return "\n".join(parts)
