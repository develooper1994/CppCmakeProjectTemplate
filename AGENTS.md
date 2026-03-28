# AGENTS.md — AI Agent Integration Guidelines

This document outlines how AI agents should interact with the CppCmakeProjectTemplate tooling.

## Core Mandates

- **Use the Unified CLI:** ALWAYS prefer `python3 scripts/tool.py <command>` over legacy scripts.
- **Command Structure:** Commands follow the pattern: `python3 scripts/tool.py <core_command|plugin> [args...]`
- **Core Commands:**
  - `build`: Build, check, clean, deploy.
  - `lib`: Library management (add, remove, list, etc.).
  - `sol`: Project orchestration (presets, toolchains, CI, doctor).
- **Plugin Commands:** Dynamically discovered from `scripts/plugins/` (e.g., `hello`, `setup`, `init`).
- **Structured Output:** Use `--json` flag for machine-readable output.
- **Non-interactive Mode:** Use `--yes` flag for automated execution.
- **Dry Run:** Use `--dry-run` to preview changes.

## Key Files & Directories

- **Dispatcher:** `scripts/tool.py` is the main entry point.
- **Core Logic:** `scripts/core/commands/` (build, lib, sol)
- **Core Utilities:** `scripts/core/utils/common.py`
- **Plugins:** `scripts/plugins/` (dynamic commands)
- **Documentation:** `docs/PLANS.md` outlines the project roadmap.

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

### Library Management

- **List Libraries:** `python3 scripts/tool.py lib list`
- **Add Library:** `python3 scripts/tool.py lib add <library-name>`
- **Remove Library:** `python3 scripts/tool.py lib remove <library-name> [--delete]`

### Project Orchestration

- **List Presets:** `python3 scripts/tool.py sol preset list`
- **Run CI:** `python3 scripts/tool.py sol ci`
- **Health Check:** `python3 scripts/tool.py sol doctor`

## Implementation Notes

The modules `scripts/build.py`, `scripts/toollib.py`, and `scripts/toolsolution.py` implement the command logic used by the unified dispatcher `scripts/tool.py`.

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
