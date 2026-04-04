"""
core/utils/config_schema.py — tool.toml validation
====================================================

Validates tool.toml against a known schema.  Reports typos, unknown keys,
type mismatches, and missing required fields with human-friendly messages.

Usage::

    from core.utils.config_schema import validate_config
    errors, warnings = validate_config(cfg)
    for e in errors:
        print(f"ERROR: {e}")
    for w in warnings:
        print(f"WARN:  {w}")
"""
from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Schema definition
# ---------------------------------------------------------------------------
# Each entry: key → (type_or_types, required, description)
# type is one of: str, int, float, bool, list, dict, or a tuple of those.

_STR = str
_INT = int
_FLOAT = (int, float)
_BOOL = bool
_LIST = list
_DICT = dict

# Top-level sections expected in tool.toml
KNOWN_SECTIONS: dict[str, str] = {
    "tool":          "Global dispatcher defaults",
    "build":         "Build command defaults",
    "perf":          "Performance command defaults",
    "security":      "Security scan defaults",
    "lib":           "Library command defaults",
    "doc":           "Documentation defaults",
    "release":       "Release command defaults",
    "hooks":         "Git hooks configuration",
    "presets":        "CMakePresets.json generation",
    "autotuner":     "Auto-tuner search space",
    "gpu":           "GPU compute backend config",
    "embedded":      "Cross-compilation / embedded defaults",
    "session":       "Runtime session state",
    "project":       "Project metadata and declarations",
    "ci":            "CI/CD configuration",
    "deps":          "Dependency manager configuration",
    "docker":        "Docker build variants",
    "cmake_modules": "CMake module selection",
    "vscode":        "VS Code workspace generation",
    "git":           "Git config file generation",
    "docs":          "Documentation generation",
    "extension":     "VS Code extension generation",
    "generate":      "Generation engine defaults",
}

# Per-section key schemas: key → (expected_type, required)
_SECTION_SCHEMAS: dict[str, dict[str, tuple[type | tuple, bool]]] = {
    "tool": {
        "default_preset":   (_STR, False),
        "default_profile":  (_STR, False),
        "log_format":       (_STR, False),
        "auto_confirm":     (_BOOL, False),
    },
    "build": {
        "preset":           (_STR, False),
        "lto":              (_BOOL, False),
        "cache_program":    (_STR, False),
        "extra_cmake_args": (_LIST, False),
        "parallel_jobs":    (_INT, False),
    },
    "perf": {
        "size_threshold_pct":   (_FLOAT, False),
        "time_threshold_pct":   (_FLOAT, False),
        "auto_detect_build_dir": (_BOOL, False),
        "bench_auto_baseline":   (_BOOL, False),
    },
    "security": {
        "fail_on_severity": (_STR, False),
        "format":           (_STR, False),
        "suppressions":     (_LIST, False),
    },
    "lib": {
        "cxx_standard":     (_STR, False),
        "default_template": (_STR, False),
        "auto_register":    (_BOOL, False),
    },
    "doc": {
        "serve_port":         (_INT, False),
        "serve_open_browser": (_BOOL, False),
        "generate":           (_BOOL, False),
        "engine":             (_STR, False),
        "generate_api_docs":  (_BOOL, False),
        "doxygen_dot":        (_BOOL, False),
        "doxygen_extract_all":(_BOOL, False),
        "mkdocs_theme":       (_STR, False),
    },
    "release": {
        "auto_push":      (_BOOL, False),
        "signing_key":    (_STR, False),
        "version_files":  (_LIST, False),
    },
    "hooks": {
        "gitleaks_config":       (_STR, False),
        "gitleaks_on_commit":    (_BOOL, False),
        "clangformat_on_commit": (_BOOL, False),
    },
    "presets": {
        "compilers":           (_LIST, False),
        "build_types":         (_LIST, False),
        "linkages":            (_LIST, False),
        "arches":              (_LIST, False),
        "allocators":          (_LIST, False),
        "cmake_minimum_major": (_INT, False),
        "cmake_minimum_minor": (_INT, False),
        "default_preset":      (_STR, False),
        "cuda_architectures":  (_STR, False),
        "generator":           (_STR, False),
        "skip_combinations":   (_LIST, False),
    },
    "autotuner": {
        "strategy":             (_STR, False),
        "oracle":               (_STR, False),
        "rounds":               (_INT, False),
        "T_init":               (_FLOAT, False),
        "T_alpha":              (_FLOAT, False),
        "flag_candidates":      (_LIST, False),
        "size_flag_candidates": (_LIST, False),
    },
    "gpu": {
        "sycl_targets": (_STR, False),
        "metal_sdk":    (_STR, False),
    },
    "embedded": {
        "default_preset":       (_STR, False),
        "arm_toolchain_prefix": (_STR, False),
        "linker_scripts_dir":   (_STR, False),
    },
    "session": {
        "last_preset":      (_STR, False),
        "default_command":  (_STR, False),
        "default_preset":   (_STR, False),
        "verbose":          (_BOOL, False),
        "json":             (_BOOL, False),
        "yes":              (_BOOL, False),
        "dry_run":          (_BOOL, False),
    },
    "project": {
        "name":          (_STR, True),
        "version":       (_STR, False),
        "description":   (_STR, False),
        "author":        (_STR, False),
        "contact":       (_STR, False),
        "license":       (_STR, False),
        "cxx_standard":  (_STR, False),
        "cmake_minimum": (_STR, False),
        "libs":          (_LIST, False),
        "apps":          (_LIST, False),
        "tests":         (_DICT, False),
    },
    "ci": {
        "provider":        (_STR, False),
        "workflows":       (_LIST, False),
        "reusable":        (_BOOL, False),
        "issue_templates": (_LIST, False),
    },
    "deps": {
        "managers": (_LIST, False),
        "vcpkg":    (_DICT, False),
        "conan":    (_DICT, False),
    },
    "docker": {
        "variants": (_LIST, False),
    },
    "cmake_modules": {
        "enabled":     (_LIST, False),
        "toolchains":  (_DICT, False),
    },
    "vscode": {
        "generate": (_BOOL, False),
    },
    "git": {
        "generate_gitignore":     (_BOOL, False),
        "generate_gitattributes": (_BOOL, False),
        "generate_editorconfig":  (_BOOL, False),
        "init":                   (_STR, False),
    },
    "docs": {
        "generate": (_BOOL, False),
        "engine":   (_STR, False),
    },
    "extension": {
        "generate": (_BOOL, False),
    },
    "generate": {
        "on_conflict":    (_STR, False),
        "backup_dir":     (_STR, False),
        "manifest_file":  (_STR, False),
        "profile":        (_STR, False),
    },
}

# Lib entry schema
_LIB_KEYS: dict[str, tuple[type | tuple, bool]] = {
    "name":         (_STR, True),
    "type":         (_STR, False),
    "template":     (_STR, False),
    "cxx_standard": (_STR, False),
    "deps":         (_LIST, False),
    "export":       (_BOOL, False),
    "benchmarks":   (_BOOL, False),
    "build_info":   (_BOOL, False),
    "fuzz":         (_BOOL, False),
    "header_only":  (_BOOL, False),
    "interface":    (_BOOL, False),
    "modules":      (_BOOL, False),
    "version":      (_STR, False),
    "description":  (_STR, False),
}

# App entry schema
_APP_KEYS: dict[str, tuple[type | tuple, bool]] = {
    "name":       (_STR, True),
    "deps":       (_LIST, False),
    "hardening":  (_BOOL, False),
    "build_info": (_BOOL, False),
    "gui":        (_BOOL, False),
    "qml":        (_BOOL, False),
    "description":(_STR, False),
}

# Valid enum-like values
_VALID_VALUES: dict[str, set[str]] = {
    "tool.default_profile": {"normal", "strict", "hardened", "extreme"},
    "tool.log_format": {"text", "json"},
    "build.cache_program": {"", "ccache", "sccache"},
    "security.fail_on_severity": {"CRITICAL", "HIGH", "MEDIUM", "LOW", "NONE"},
    "security.format": {"text", "json"},
    "project.license": {"MIT", "Apache-2.0", "GPL-3.0", "LGPL-3.0", "BSD-2-Clause", "BSD-3-Clause", "Unlicense", "MPL-2.0", "ISC", "BSL-1.0"},
    "project.tests.framework": {"gtest", "catch2", "doctest"},
    "autotuner.strategy": {"hill", "grid", "random", "anneal"},
    "autotuner.oracle": {"speed", "size", "instructions"},
    "generate.on_conflict": {"ask", "overwrite", "skip", "backup"},
    "generate.profile": {"full", "minimal", "library", "app", "embedded"},
    "ci.provider": {"github", "gitlab", "azure"},
    "git.init": {"auto", "always", "never"},
}


# ---------------------------------------------------------------------------
# Levenshtein distance for typo suggestions
# ---------------------------------------------------------------------------
def _levenshtein(a: str, b: str) -> int:
    if len(a) < len(b):
        return _levenshtein(b, a)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        curr = [i + 1]
        for j, cb in enumerate(b):
            curr.append(min(prev[j + 1] + 1, curr[j] + 1,
                            prev[j] + (0 if ca == cb else 1)))
        prev = curr
    return prev[-1]


def _suggest(key: str, valid_keys: set[str], max_distance: int = 2) -> str | None:
    """Return closest matching key if within edit distance."""
    best, best_dist = None, max_distance + 1
    for vk in valid_keys:
        d = _levenshtein(key, vk)
        if d < best_dist:
            best, best_dist = vk, d
    return best if best_dist <= max_distance else None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_config(cfg: dict[str, Any]) -> tuple[list[str], list[str]]:
    """
    Validate a loaded tool.toml config dict.

    Returns (errors, warnings) where each is a list of human-readable messages.
    Errors indicate definite problems; warnings indicate possible issues.
    """
    errors: list[str] = []
    warnings: list[str] = []

    # 1. Check for unknown top-level sections
    for section in cfg:
        if section not in KNOWN_SECTIONS:
            msg = f"[{section}]: unknown section"
            suggestion = _suggest(section, set(KNOWN_SECTIONS))
            if suggestion:
                msg += f" — did you mean [{suggestion}]?"
            warnings.append(msg)

    # 2. Validate each known section
    for section, schema in _SECTION_SCHEMAS.items():
        if section not in cfg:
            continue
        val = cfg[section]
        if not isinstance(val, dict):
            errors.append(f"[{section}]: expected a table, got {type(val).__name__}")
            continue

        # Check keys within section
        for key in val:
            if key in schema:
                expected_type, _required = schema[key]
                actual = val[key]
                if not isinstance(actual, expected_type):
                    errors.append(
                        f"[{section}].{key}: expected {_type_name(expected_type)}, "
                        f"got {type(actual).__name__} ({actual!r})"
                    )
                # Check enum values
                enum_key = f"{section}.{key}"
                if enum_key in _VALID_VALUES and isinstance(actual, str):
                    if actual not in _VALID_VALUES[enum_key]:
                        errors.append(
                            f"[{section}].{key}: invalid value {actual!r} — "
                            f"expected one of: {', '.join(sorted(_VALID_VALUES[enum_key]))}"
                        )
            else:
                msg = f"[{section}].{key}: unknown key"
                suggestion = _suggest(key, set(schema))
                if suggestion:
                    msg += f" — did you mean '{suggestion}'?"
                warnings.append(msg)

        # Check required keys
        for key, (_, required) in schema.items():
            if required and key not in val:
                errors.append(f"[{section}].{key}: required but missing")

    # 3. Validate lib entries
    libs = cfg.get("project", {}).get("libs", [])
    if isinstance(libs, list):
        for i, lib in enumerate(libs):
            if not isinstance(lib, dict):
                errors.append(f"[[project.libs]][{i}]: expected a table, got {type(lib).__name__}")
                continue
            _validate_entry(lib, _LIB_KEYS, f"[[project.libs]][{i}]", errors, warnings)

    # 4. Validate app entries
    apps = cfg.get("project", {}).get("apps", [])
    if isinstance(apps, list):
        for i, app in enumerate(apps):
            if not isinstance(app, dict):
                errors.append(f"[[project.apps]][{i}]: expected a table, got {type(app).__name__}")
                continue
            _validate_entry(app, _APP_KEYS, f"[[project.apps]][{i}]", errors, warnings)

    # 5. Cross-checks
    _cross_validate(cfg, errors, warnings)

    return errors, warnings


def _validate_entry(
    entry: dict[str, Any],
    schema: dict[str, tuple[type | tuple, bool]],
    prefix: str,
    errors: list[str],
    warnings: list[str],
) -> None:
    """Validate a single lib or app entry."""
    for key in entry:
        if key in schema:
            expected_type, _ = schema[key]
            if not isinstance(entry[key], expected_type):
                errors.append(
                    f"{prefix}.{key}: expected {_type_name(expected_type)}, "
                    f"got {type(entry[key]).__name__}"
                )
        else:
            msg = f"{prefix}.{key}: unknown key"
            suggestion = _suggest(key, set(schema))
            if suggestion:
                msg += f" — did you mean '{suggestion}'?"
            warnings.append(msg)

    for key, (_, required) in schema.items():
        if required and key not in entry:
            errors.append(f"{prefix}.{key}: required but missing")


def _cross_validate(cfg: dict[str, Any], errors: list[str], warnings: list[str]) -> None:
    """Cross-section consistency checks."""
    project = cfg.get("project", {})
    libs = project.get("libs", [])
    apps = project.get("apps", [])

    if isinstance(libs, list) and isinstance(apps, list):
        lib_names = {lib["name"] for lib in libs if isinstance(lib, dict) and "name" in lib}

        # Check app deps reference declared libs
        for i, app in enumerate(apps):
            if not isinstance(app, dict):
                continue
            for dep in app.get("deps", []):
                if dep not in lib_names:
                    errors.append(
                        f"[[project.apps]][{i}] ({app.get('name', '?')}): "
                        f"dep '{dep}' references undeclared library — "
                        f"known libs: {', '.join(sorted(lib_names)) or '(none)'}"
                    )

        # Check for duplicate lib names
        seen: dict[str, int] = {}
        for i, lib in enumerate(libs):
            if not isinstance(lib, dict):
                continue
            name = lib.get("name", "")
            if name in seen:
                errors.append(
                    f"[[project.libs]][{i}]: duplicate library name '{name}' "
                    f"(first declared at index {seen[name]})"
                )
            else:
                seen[name] = i

        # Check for duplicate app names
        seen_apps: dict[str, int] = {}
        for i, app in enumerate(apps):
            if not isinstance(app, dict):
                continue
            name = app.get("name", "")
            if name in seen_apps:
                errors.append(
                    f"[[project.apps]][{i}]: duplicate app name '{name}' "
                    f"(first declared at index {seen_apps[name]})"
                )
            else:
                seen_apps[name] = i

        # Check lib deps reference declared libs
        for i, lib in enumerate(libs):
            if not isinstance(lib, dict):
                continue
            for dep in lib.get("deps", []):
                if dep not in lib_names:
                    errors.append(
                        f"[[project.libs]][{i}] ({lib.get('name', '?')}): "
                        f"dep '{dep}' references undeclared library — "
                        f"known libs: {', '.join(sorted(lib_names)) or '(none)'}"
                    )

        # Validate template names
        _VALID_TEMPLATES = {"exported", "fuzzable", "hasher", "default", "normal"}
        for i, lib in enumerate(libs):
            if not isinstance(lib, dict):
                continue
            tmpl = lib.get("template", "")
            if tmpl and tmpl not in _VALID_TEMPLATES:
                errors.append(
                    f"[[project.libs]][{i}] ({lib.get('name', '?')}): "
                    f"invalid template '{tmpl}' — "
                    f"expected one of: {', '.join(sorted(_VALID_TEMPLATES))}"
                )

        # Detect circular dependencies among libs
        _detect_circular_deps(libs, lib_names, errors)


def _detect_circular_deps(
    libs: list[Any], lib_names: set[str], errors: list[str]
) -> None:
    """Detect circular dependencies among library declarations."""
    adj: dict[str, list[str]] = {}
    for lib in libs:
        if not isinstance(lib, dict) or "name" not in lib:
            continue
        name = lib["name"]
        adj[name] = [d for d in lib.get("deps", []) if d in lib_names]

    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {n: WHITE for n in adj}

    def dfs(node: str, path: list[str]) -> bool:
        color[node] = GRAY
        path.append(node)
        for dep in adj.get(node, []):
            if color.get(dep) == GRAY:
                cycle_start = path.index(dep)
                cycle = path[cycle_start:] + [dep]
                errors.append(
                    f"circular dependency detected: {' → '.join(cycle)}"
                )
                return True
            if color.get(dep) == WHITE:
                if dfs(dep, path):
                    return True
        path.pop()
        color[node] = BLACK
        return False

    for lib_name in adj:
        if color[lib_name] == WHITE:
            dfs(lib_name, [])


def _type_name(t: type | tuple) -> str:
    if isinstance(t, tuple):
        return " or ".join(x.__name__ for x in t)
    return t.__name__


# ---------------------------------------------------------------------------
# CLI entrypoint (can be used standalone)
# ---------------------------------------------------------------------------

def validate_file(path: "str | None" = None) -> tuple[list[str], list[str]]:
    """Load and validate a tool.toml file. Returns (errors, warnings)."""
    from core.utils.config_loader import load_tool_config
    from pathlib import Path

    cfg_path = Path(path) if path else None
    cfg = load_tool_config(cfg_path)
    return validate_config(cfg)
