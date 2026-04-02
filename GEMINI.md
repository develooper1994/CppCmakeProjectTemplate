# GEMINI.md — Project Overview for AI Assistants

## TL;DR

This is a **professional C++ CMake project template** with full automation tooling.
**Do not use legacy scripts directly.** Use the unified entrypoint `scripts/tool.py` to manage everything.

## Quick Reference

```bash
# Create a new project (interactive wizard)
python3 scripts/tool.py new MyProject

# Build + test (always run this after changes)
python3 scripts/tool.py build check --no-sync

# Add a library
python3 scripts/tool.py lib add my_lib

# Generate project from tool.toml (with profile)
python3 scripts/tool.py generate --profile library --explain

# License recommendation
python3 scripts/tool.py license recommend

# All library management
python3 scripts/tool.py lib --help

# Project-level management (presets, toolchains, repos, CI)
python3 scripts/tool.py sol --help

# Check health
python3 scripts/tool.py sol doctor
```

## Repository Structure

```
apps/           Executable apps (main_app prints full build info at runtime)
libs/           Libraries — each independent, versioned, with its own BuildInfo
tests/unit/     GoogleTest per-library test suites
cmake/          CMake modules + auto-generated C++ headers
scripts/
  tool.py       → Central Dispatcher (Grand Entrypoint)
  core/
    commands/   → Core logic (build, lib, sol, generate, new, license)
    generator/  → Project generator engine, wizard, profiles
    utils/      → Infrastructure (common.py)
  plugins/      → Dynamic plugins (setup, hooks, init)
extension/      VS Code extension (C++ CMake Scaffolder)
docs/
  PLANS.md      → Strategic Roadmap
```

## Key Design Principles

1. **Unified CLI** — One tool to rule them all: `python3 scripts/tool.py`
2. **Structured Logging** — All operations are logged with severity levels
3. **Target-based CMake** — No global flags, everything scoped to targets
4. **Cross-platform presets** — Covers GCC/Clang/MSVC/ARM

## Execution Protocol

Analyze → Impact → Plan → Implement → Integrate → Validate → Output

Always end with: `python3 scripts/tool.py build check --no-sync`
