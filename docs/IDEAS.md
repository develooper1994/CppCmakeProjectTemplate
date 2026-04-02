# Ideas & Future Directions

A collection of improvement ideas for the project, organized by category. Items here are aspirational — not committed to any timeline.

---

## Generator Completion

- **CMakePresets Integration:** Wire `presets.py` into the generator engine so `tool generate` also regenerates `CMakePresets.json` from `tool.toml [presets]`.
- **C++ Template Library:** Templatize custom C++ code (secure_ops, fuzzable patterns) so new projects get domain-relevant stubs rather than generic boilerplate.
- **CI Workflow Generation:** Move CI configs from static tracking (hash-only) to full generation from `tool.toml [ci]` section.
- **Docs Generation:** Generate `docs/*.md` from `tool.toml` metadata — auto-create README, QUICK_START, etc.
- **Generated File Deletion:** When a component is disabled in `tool.toml`, automatically clean up previously generated files (manifest-based tracking).
- **Benchmark Component:** Add a generator component for benchmark scaffolding (Google Benchmark / Catch2 Benchmark). Currently benchmarks have no generator equivalent.

## New Capabilities

- **Shell Completion:** Bash/Zsh/Fish completions for `tool.py` commands — generated from argparse definitions.
- **DevContainer:** `.devcontainer/devcontainer.json` generation with correct extensions, mounts, and post-create commands.
- **Migration Wizard:** `tool migrate` to upgrade existing projects from older template versions. Read manifest, detect drift, offer incremental updates.
- **Monorepo Support:** Multiple independent `tool.toml` files in subdirectories, with a root-level orchestrator (`tool workspace`).
- **Plugin System v2:** Community plugins installable via `tool plugin install <name>` from a plugin registry.
- **WebAssembly Target:** Emscripten toolchain + preset for WASM builds.

## Developer Experience

- **Watch Mode:** `tool build --watch` auto-rebuilds on source changes (inotify/fswatch).
- **Error Diagnostics:** Human-friendly error messages with suggested fixes — similar to Rust's compiler diagnostics.
- **Project Templates Gallery:** A curated set of starter templates (game engine, embedded firmware, networking library) selectable via the wizard.
- **Interactive TUI v2:** Full-screen TUI mode with menu navigation, build status dashboard, log viewer.

## Quality & Security

- **SBOM Generation:** Software Bill of Materials (SPDX/CycloneDX) auto-generated during release.
- **Reproducible Build Verification:** Bitwise reproducibility check — build twice, compare hashes.
- **Dependency Update Bot:** `tool deps update` checks for newer versions across vcpkg/Conan/pip and proposes upgrades.

## Architecture & Philosophy

- **`tool init` (In-Place Adoption):** Like `cargo init` — run inside an existing directory containing C++ files, auto-detect sources, generate `tool.toml` + CMake scaffolding around them. Inverse of `tool new`.
- **Minimal Seed Mode:** Reduce the repo to only `scripts/` + `tool.toml` + `.gitignore`. First `tool generate` bootstraps everything. CI clones → generates → builds. Template users never see generated files in git.
- **Config Validation & Schema:** JSON Schema or Pydantic validation for `tool.toml`. Report typos, unknown keys, type mismatches with human-friendly messages before generation runs.
- **Component Dependency Graph:** Let generator components declare dependencies on each other. Auto-order generation, skip components whose inputs haven't changed.
- **Incremental Generation:** Only regenerate files whose inputs (tool.toml sections, templates) changed since last run. Track input hashes alongside output hashes in manifest.

## Radical Ideas

- **Self-Hosting:** The generator generates its own `scripts/` infrastructure — full bootstrap from a minimal seed.
- **Language Server Protocol (LSP) for tool.toml:** IDE support with completion, validation, and hover docs for `tool.toml` editing.
- **AI-Assisted Code Generation:** Integrate LLM APIs for generating domain-specific C++ code based on `tool.toml` metadata and library descriptions.
- **Multi-Language Scaffolding:** Extend the generator to scaffold Rust/Go/Python companion libraries alongside C++, with FFI bindings auto-generated.
- **Nix Flake Support:** `flake.nix` generation for fully reproducible development environments — hermetic toolchain pinning without Docker overhead.
