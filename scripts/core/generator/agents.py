"""
core/generator/agents.py — AI agent instruction file generator component
========================================================================

Generates AI agent configuration files for multiple AI tools:

- ``AGENTS.md`` — Universal AI agent guidelines (GitHub Copilot, Claude, etc.)
- ``.github/copilot-instructions.md`` — GitHub Copilot workspace instructions
- ``.cursorrules`` — Cursor AI project rules
- ``.clinerules`` — Cline AI project rules

All files are generated from ``tool.toml`` project metadata so they stay
in sync with the actual project structure.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path
    from core.generator.engine import ProjectContext


def _lib_names(ctx: "ProjectContext") -> list[str]:
    """Extract library names from context."""
    if isinstance(ctx.libs, dict):
        return sorted(ctx.libs.keys())
    if isinstance(ctx.libs, list):
        return sorted(lib.get("name", "") for lib in ctx.libs if lib.get("name"))
    return []


def _app_names(ctx: "ProjectContext") -> list[str]:
    """Extract app names from context."""
    if isinstance(ctx.apps, dict):
        return sorted(ctx.apps.keys())
    if isinstance(ctx.apps, list):
        return sorted(app.get("name", "") for app in ctx.apps if app.get("name"))
    return []


def _build_structure_tree(ctx: "ProjectContext") -> str:
    """Build a compact repository structure description."""
    lines = []
    name = ctx.name or "CppProject"
    libs = _lib_names(ctx)
    apps = _app_names(ctx)

    lines.append(f"# {name} Repository Structure")
    lines.append("```")
    lines.append("apps/           Executable applications")
    for app in apps:
        lines.append(f"  {app}/")
    lines.append("libs/           Libraries")
    for lib in libs:
        lines.append(f"  {lib}/")
    lines.append("tests/unit/     GoogleTest per-library test suites")
    lines.append("tests/fuzz/     Fuzz testing harnesses")
    lines.append("cmake/          CMake modules + auto-generated headers")
    lines.append("scripts/        Build automation & generator tooling")
    lines.append("  tool.py       Central CLI dispatcher")
    lines.append("docs/           Documentation")
    lines.append("docker/         Dockerfiles")
    lines.append("```")
    return "\n".join(lines)


def _gen_agents_md(ctx: "ProjectContext") -> str:
    """Generate AGENTS.md — universal AI agent guidelines."""
    name = ctx.name or "CppProject"
    std = ctx.cxx_standard or "17"
    libs = _lib_names(ctx)
    apps = _app_names(ctx)

    lib_list = ", ".join(f"`{l}`" for l in libs) if libs else "(none yet)"
    app_list = ", ".join(f"`{a}`" for a in apps) if apps else "(none yet)"

    return f"""# AGENTS.md — AI Agent Integration Guidelines

This document outlines how AI agents should interact with the **{name}** project.

> **AUTO-GENERATED** — Edit `tool.toml` and re-run `tool generate` to update.

## Core Mandates

- **Use the Unified CLI:** ALWAYS prefer `python3 scripts/tool.py <command>` over manual CMake.
- **Command Structure:** `python3 scripts/tool.py <core_command|plugin> [args...]`
- **Core Commands:**
  - `build`: Build, check, clean, deploy
  - `lib`: Library management (add, remove, list, deps, export)
  - `sol`: Project orchestration (presets, toolchains, CI, doctor)
  - `new`: Interactive project creation wizard
  - `generate`: Generate project from `tool.toml` (profiles, feature toggles)
  - `validate`: Schema-based validation for `tool.toml`
- **Structured Output:** Use `--json` flag for machine-readable output.
- **Non-interactive Mode:** Use `--yes` flag for automated execution.
- **Dry Run:** Use `--dry-run` to preview changes.

## Project Overview

| Property | Value |
| -------- | ----- |
| Name | {name} |
| C++ Standard | C++{std} |
| Libraries | {lib_list} |
| Applications | {app_list} |

## Key Files & Directories

- **Dispatcher:** `scripts/tool.py` — main entry point
- **Core Logic:** `scripts/core/commands/` (build, lib, sol, generate, new)
- **Generator Engine:** `scripts/core/generator/` (engine, profiles, manifest)
- **Configuration:** `tool.toml` — single source of truth
- **CMake Modules:** `cmake/` — reusable CMake functions

{_build_structure_tree(ctx)}

## Recommended Workflows

### Build & Validate
```bash
python3 scripts/tool.py build                    # build project
python3 scripts/tool.py build check --no-sync    # build + test + lint
```

### Library Management
```bash
python3 scripts/tool.py lib list                 # list all libraries
python3 scripts/tool.py lib add <name>           # add a new library
python3 scripts/tool.py lib remove <name>        # remove a library
```

### Code Generation
```bash
python3 scripts/tool.py generate                 # regenerate from tool.toml
python3 scripts/tool.py generate --dry-run       # preview changes
python3 scripts/tool.py validate                 # validate tool.toml
```

## Coding Standards

- `PascalCase` for classes/structs, `lower_case` for functions/variables/namespaces
- `std::string_view` for const string parameters
- Smart pointers over raw pointers
- Arrange-Act-Assert for unit tests
- C++ Standard: C++{std}
- All CMake must be target-scoped — no global flags
- Never touch `external/` directly
- Every library needs: `CMakeLists.txt`, `README.md`, `include/<name>/`, `docs/`

## Security Considerations

- Always sanitize user input before passing it to shell commands
- Use the `run_proc` utility from `core.utils.common` for executing external processes
- Be mindful of secrets management

## Documentation Governance

- **`docs/ROADMAP.md`** = upcoming/active work & ideas
- **`docs/CAPABILITIES.md`** = completed features
- When a feature is done: move from ROADMAP.md → CAPABILITIES.md
"""


def _gen_copilot_instructions(ctx: "ProjectContext") -> str:
    """Generate .github/copilot-instructions.md — GitHub Copilot workspace instructions."""
    name = ctx.name or "CppProject"
    std = ctx.cxx_standard or "17"
    libs = _lib_names(ctx)
    apps = _app_names(ctx)

    lib_cmds = ""
    if libs:
        lib_cmds = "\n".join(f"  - `{l}`" for l in libs)

    return f"""# GitHub Copilot Instructions

## Project Overview

This is a **C++ CMake project** ({name}) with full automation tooling.
Read `AGENTS.md` for the complete reference.

> **AUTO-GENERATED** — Edit `tool.toml` and re-run `tool generate` to update.

## Critical: Use Existing Tools

**Before writing any code or CMake, check if the tooling already handles it:**

```bash
python3 scripts/tool.py lib --help       # Library management
python3 scripts/tool.py sol --help       # Project orchestration
python3 scripts/tool.py build --help     # Build automation
python3 scripts/tool.py new --help       # Project creation wizard
python3 scripts/tool.py generate --help  # Code generation with profiles
```

## Adding a Library

```bash
python3 scripts/tool.py lib add my_lib               # normal library
python3 scripts/tool.py lib add my_lib --header-only  # header-only
python3 scripts/tool.py lib add my_lib --interface    # interface target
```

## Validation (run after every change)

```bash
python3 scripts/tool.py build check --no-sync
```

## Libraries
{lib_cmds if lib_cmds else "No libraries configured yet."}

## Code Conventions

- `PascalCase` for classes/structs, `lower_case` for functions/variables/namespaces
- `std::string_view` for const string parameters
- Smart pointers over raw pointers
- C++{std} standard
- Arrange-Act-Assert for unit tests
- All CMake must be target-scoped — no global flags
"""


def _gen_cursorrules(ctx: "ProjectContext") -> str:
    """Generate .cursorrules — Cursor AI project rules."""
    name = ctx.name or "CppProject"
    std = ctx.cxx_standard or "17"

    return f"""# Cursor Rules for {name}
# AUTO-GENERATED — Edit tool.toml and re-run `tool generate` to update.

You are working on a C++{std} CMake project called {name}.

## Key Rules
- Use `python3 scripts/tool.py <command>` for all build/lib/generation tasks
- Read `AGENTS.md` for full AI agent integration guidelines
- All CMake must be target-scoped — no global flags
- Every library needs: CMakeLists.txt, README.md, include/<name>/, docs/
- Use PascalCase for classes, lower_case for functions/variables
- Use std::string_view for const string parameters
- Prefer smart pointers over raw pointers
- Run `python3 scripts/tool.py build check --no-sync` after changes

## Project Structure
- `tool.toml` — single source of truth for project configuration
- `scripts/tool.py` — unified CLI dispatcher
- `libs/` — library sources
- `apps/` — application sources
- `cmake/` — CMake modules
"""


def _gen_clinerules(ctx: "ProjectContext") -> str:
    """Generate .clinerules — Cline AI project rules."""
    name = ctx.name or "CppProject"
    std = ctx.cxx_standard or "17"

    return f"""# Cline Rules for {name}
# AUTO-GENERATED — Edit tool.toml and re-run `tool generate` to update.

## Project: {name} (C++{std})

## Commands
- Build: `python3 scripts/tool.py build`
- Test: `python3 scripts/tool.py build check --no-sync`
- Add lib: `python3 scripts/tool.py lib add <name>`
- Generate: `python3 scripts/tool.py generate`
- Validate: `python3 scripts/tool.py validate`

## Conventions
- Read AGENTS.md for full guidelines
- PascalCase for classes, lower_case for functions
- std::string_view for const string params
- Smart pointers over raw pointers
- Target-scoped CMake only
"""


def _gen_claude_instructions(ctx: "ProjectContext") -> str:
    """Generate .claude/instructions.md — Claude Code project instructions."""
    name = ctx.name or "CppProject"
    std = ctx.cxx_standard or "17"

    return f"""# Claude Code Instructions for {name}
<!-- AUTO-GENERATED — Edit tool.toml and re-run `tool generate` to update. -->

## Project Context
C++{std} CMake project with Python automation. All configuration in `tool.toml`.
Read `AGENTS.md` for full AI agent guidelines.

## Essential Commands
```bash
python3 scripts/tool.py build check --no-sync  # Validate everything
python3 scripts/tool.py lib add <name>          # Add library
python3 scripts/tool.py generate                # Regenerate from tool.toml
python3 scripts/tool.py validate                # Validate configuration
```

## Conventions
- PascalCase for classes, lower_case for functions/variables
- std::string_view for const string parameters
- Smart pointers over raw pointers
- Target-scoped CMake only — no global flags
- GoogleTest with Arrange-Act-Assert pattern
"""


def generate_all(ctx: "ProjectContext", target_dir: "Path") -> dict[str, str]:
    """Return AI agent instruction files."""
    files: dict[str, str] = {
        "AGENTS.md": _gen_agents_md(ctx),
        ".github/copilot-instructions.md": _gen_copilot_instructions(ctx),
        ".cursorrules": _gen_cursorrules(ctx),
        ".clinerules": _gen_clinerules(ctx),
        ".claude/instructions.md": _gen_claude_instructions(ctx),
    }
    return files
