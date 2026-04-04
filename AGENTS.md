
# AGENTS.md — AI Agent Integration Guidelines

> **Canonical Documentation:**
> For full CLI and feature documentation, see [docs/USAGE.md](docs/USAGE.md) (CLI reference) and [docs/CAPABILITIES.md](docs/CAPABILITIES.md) (completed features). This file covers agent integration and automation notes only.

> **Command Naming:**
> All command examples use the form `python3 scripts/tool.py <command> <subcommand>`, e.g., `python3 scripts/tool.py nix generate`.

> **Auto-Detection:**
> Agents should use `python3 scripts/tool.py sol doctor --show-auto` for a full environment summary and to view all auto-detected features.

This document outlines how AI agents should interact with the CppCmakeProjectTemplate tooling.

## Core Mandates

- **Use the Unified CLI:** ALWAYS prefer `python3 scripts/tool.py <command>` over legacy scripts.
- **Command Structure:** Commands follow the pattern: `python3 scripts/tool.py <core_command|plugin> [args...]`
- **Core Commands:**
  - `build`: Build, check, clean, deploy.
  - `lib`: Library management (add, remove, list, etc.).
  - `sol`: Project orchestration (presets, toolchains, CI, doctor).
  - `new`: Interactive project creation wizard.
  - `adopt`: In-place adoption of existing C++ projects (auto-detect sources, generate tool.toml + CMake).
  - `generate`: Generate project from `tool.toml` (profiles, feature toggles).
  - `validate`: Schema-based validation for `tool.toml` (typos, type checks, cross-references).
  - `completion`: Shell completion scripts for Bash/Zsh/Fish.
  - `license`: License recommendation and selection.
- **Plugin Commands:** Dynamically discovered from `scripts/plugins/` (e.g., `hello`, `setup`, `init`).
- **Structured Output:** Use `--json` flag for machine-readable output.
- **Non-interactive Mode:** Use `--yes` flag for automated execution.
- **Dry Run:** Use `--dry-run` to preview changes.

## Key Files & Directories

- **Dispatcher:** `scripts/tool.py` is the main entry point.
- **Core Logic:** `scripts/core/commands/` (build, lib, sol, generate, new, adopt, validate, completion, license, deps, doc, format, perf, presets, release, security, session, plugins, sbom, diagnostics, nix, migrate, templates)
- **Generator Engine:** `scripts/core/generator/` (engine, wizard, profiles, merge, manifest)
- **Core Utilities:** `scripts/core/utils/common.py`
- **Plugins:** `scripts/plugins/` (dynamic commands)
- **Documentation:** `docs/ROADMAP.md` (roadmap & ideas), `docs/CAPABILITIES.md` (completed features), `docs/USAGE.md` (CLI reference)

### Repository Structure

```
apps/           Executable apps (main_app, demo_app, extreme_app, gui_app)
libs/           Libraries — each independent, versioned, with its own BuildInfo
tests/unit/     GoogleTest per-library test suites
tests/fuzz/     Fuzz testing harnesses (libFuzzer)
cmake/          CMake modules + auto-generated C++ headers
scripts/
  tool.py       → Central Dispatcher (Grand Entrypoint)
  core/
    commands/   → Core logic (build, lib, sol, generate, new, license)
    generator/  → Project generator engine, wizard, profiles, 31 tests
    utils/      → Infrastructure (common.py)
  plugins/      → Dynamic plugins (setup, hooks, init, verify)
extension/      VS Code extension (C++ CMake Scaffolder)
docs/           Documentation (PLANS, CAPABILITIES, USAGE, IDEAS, etc.)
docker/         Dockerfiles (Ubuntu, Alpine, Zig-musl)
triplets/       vcpkg custom triplets (musl static builds)
```

## Documentation Governance

- **ROADMAP.md** contains upcoming work, active tasks, backlog items, and future ideas.
- **CAPABILITIES.md** contains completed, verified capabilities.
- When a plan/feature is **fully implemented and verified**, the agent **MUST** move its description from `ROADMAP.md` to `CAPABILITIES.md` and remove it from `ROADMAP.md`.
- Never leave completed items in `ROADMAP.md` — it must only reflect remaining or in-progress work.
- New planned work is always added to `ROADMAP.md` first.

## Recommended Workflows

### Project Setup & Build

1. **Clone & Enter:**

    ```bash
    git clone <repository_url>
    cd <repository_directory>
    ```

2. **Install Dependencies:**

    ```bash
    python3 scripts/tool.py setup --install
    ```

3. **Build & Check:**

    ```bash
    python3 scripts/tool.py build check --no-sync
    ```

### Project Creation

- **Interactive Wizard:** `python3 scripts/tool.py new <name>`
- **Non-Interactive:** `python3 scripts/tool.py new <name> --non-interactive`
- **With Profile:** `python3 scripts/tool.py generate --profile library --target-dir ./MyLib`
- **License Help:** `python3 scripts/tool.py license recommend`

### Library Management

- **List Libraries:** `python3 scripts/tool.py lib list`
- **Add Library:** `python3 scripts/tool.py lib add <library-name>`
- **Remove Library:** `python3 scripts/tool.py lib remove <library-name> [--delete]`

### Project Orchestration

- **List Presets:** `python3 scripts/tool.py sol preset list`
- **Run CI:** `python3 scripts/tool.py sol ci`
- **Health Check:** `python3 scripts/tool.py sol doctor`

## Implementation Notes

The packages `scripts/core/commands/build/`, `scripts/core/commands/lib/`, `scripts/core/commands/sol/`, and `scripts/core/commands/perf/` implement the command logic used by the unified dispatcher `scripts/tool.py`.

- Public interface: use `python3 scripts/tool.py <command>` (e.g. `tool lib`, `tool sol`, `tool build`).
- Internal modules: the files above are internal implementation details — do not call them directly from outside the `scripts/` package.

## Security Considerations

- Always sanitize user input before passing it to shell commands.
- Prefer using the `run_proc` utility from `core.utils.common` for executing external processes.
- Be mindful of secrets management, especially when interacting with external services or APIs.

## Coding Standards

- Adhere to Python's PEP 8 style guide.
- Use type hints and docstrings for clarity.
- Prefer structured logging via `core.utils.common.Logger`.

## Module Splitting Guidelines

- Conservative modularization: prefer grouping related code together. Only split files when a clear separation of concerns or testability benefit exists.
- Avoid the "lowest common denominator" trap: don't split purely for potential reuse across unrelated components.
- Agents must follow this guideline when modifying or refactoring repository code — prefer fewer, cohesive modules and ask the maintainer before aggressive decomposition.

## Large-Scale Change Workflow

For changes that touch multiple files, introduce new subsystems, or carry meaningful risk of regression, agents **MUST** follow this workflow without exception.

### Status Marks

| Mark | Meaning |
| ---- | ------- |
| ✅ DONE | Verified complete — tests pass, committed |
| ⏳ IN PROGRESS | Currently being worked on |
| 🔜 DEFERRED | Planned but not started |
| 🚧 PARTIAL | Started but blocked or incomplete |
| ❌ FAILED | Attempted and could not complete; reason noted |

### Step-by-Step Protocol

1. **Plan first.** Before touching any file, write a plan (in session memory or inline). List every file to be changed, what changes are needed, and the execution order. Note dependencies between steps.

2. **Open a feature branch.** Never commit large-scope changes directly to `main`.

   ```bash
   git checkout -b feature/<short-description>
   ```

3. **Work in small, testable increments.** Complete one logical unit at a time. Mark it ✅ DONE or 🚧 PARTIAL in the plan before moving on.

4. **Read before every edit.** Before modifying a file, re-read the relevant section. Confirm the context matches expectations. If something looks different from the plan, re-evaluate before proceeding.

5. **Test after every step.**
   - Prefer `python3 scripts/tool.py build check --no-sync` for quick validation.
   - If the changed component has unit tests, run them specifically first.
   - If no tests exist for new functionality, write meaningful ones before committing.
   - A failing test means either the code or the test is wrong — check both.

6. **Commit when a step is verified green.**

   ```bash
   git add <files>
   git commit -m "feat/fix: <scope>: <description>"
   ```

   Do not batch multiple logical changes into a single commit.

7. **Repeat steps 3–6** for each remaining plan item. Re-read the plan after each commit to confirm alignment.

8. **Merge to main only when everything is ✅ DONE.**

   ```bash
   git checkout main
   git merge --no-ff feature/<short-description>
   git branch -d feature/<short-description>
   ```

9. **Delete the feature branch.** Do not leave stale branches.

### Scope Threshold — When This Workflow Applies

Apply this workflow when any of the following is true:

- More than 2 files are modified in a single logical change.
- A new subsystem, CLI command, or CMake module is introduced.
- Changes affect the build system, CI, or test infrastructure.
- The change involves non-trivial algorithm or data-structure work.
