# CppCmakeProjectTemplate — Plans & Capabilities

This document lists the project's current capabilities, governance policies, and roadmap in priority order.

---

## ✅ Current Capabilities

### Unified CLI & Tooling Framework

- **Unified CLI (`tool.py`):** A single entrypoint that manages all commands (`build`, `lib`, `sol`) and dynamic plugins (`plugins/`).
- **Modern Directory Layout:** Clear separation between infrastructure (`core/utils`), command logic (`core/commands`) and plugins (`plugins/`).
- **Structured Logging:** Standard log levels and persistent log storage.
- **Standardized Results:** Commands return a `CLIResult` and support `--json` for automation.
- **Clean Environment:** Legacy scripts consolidated into a single professional interface.

### Recent Additions

- **Shared Session Persistence:** `scripts/core/utils/common.py` now provides `load_session()`, `save_session()`, and `backup_session()` used by both `tool.py` and `tui.py` via a shared `.session.json` file.
- **Verification Harness:** `scripts/verify_full.py` automates build/test/extension and library flows and logs results to `build_logs/verify.log` for reproducible verification.
- **Python Environment Automation:** `scripts/setup_python_env.py` creates cross-platform virtual environments (`--recreate`, `--install`) and a CI workflow `.github/workflows/create_envs.yml` creates envs on Ubuntu/macOS/Windows.
- **Extension Packaging Hardened:** Extension build flow hardened; `extension/package.json` includes a minimal `build` script and the packaging step reliably produces a `.vsix` under `extension/`.
- **Versioning & Release:** Project version synchronized (bumped) and tag `v1.03` created and pushed; packaging and release steps were exercised in the verification run.
- **Library Packaging Helpers:** `core.libpkg` refactored to a modular helper surface; `tool lib` commands use these helpers for create/export/remove flows.
- **Cleanup & Consolidation:** Legacy shim files removed or consolidated under `scripts/core/`; helpful debug logs added under `build_logs/`.
- **Logging & Performance:** Logger I/O path optimized and small helper functions cached to reduce repeated file reads.

### Build System

- **Modern CMake (3.25+):** Target-based structure with no global flags.
- **Preset Matrix:** Ready presets for Linux, Windows, macOS and Embedded (ARM).
- **MSVC Consistency:** Automatic selection of `/MT` or `/MD` when appropriate.

### Compile-time Build Metadata

- **Per-Target BuildInfo:** Per-target versioning and git metadata support.
- **Dynamic Feature Flags:** Feature toggles controlled at build time.

### Quality & CI/CD

- **Testing:** Support for GoogleTest, Catch2, Boost.Test and QTest.
- **Quality Gates:** ASan, UBSan, TSan, Clang-Tidy and Cppcheck integration.
- **CI/CD:** GitHub Actions multi-platform matrix builds.

---

## 🚀 Roadmap

### Phase 1: Foundation & Unified CLI — Completed

- **Modular Dispatcher:** ✅ DONE
- **Command Contracts:** ✅ DONE
- **Structured Logging:** ✅ DONE
- **Plugin Discovery:** ✅ DONE
- **Migration & Cleanup:** ✅ DONE (legacy scripts consolidated)
- **Refactoring & Core Migration:** ✅ DONE (command logic moved under `core/commands`)

### Phase 2: Distribution & Template Engine — Completed

- **Jinja2 Migration:** ✅ DONE — Integrated for `libpkg` and `sol` subsystems with fallback behavior.
- **Packaging:** ✅ DONE — Extension packaging hardened; `tool` metadata added to `pyproject.toml`.
- **Bootstrap (`tool setup`):** ✅ DONE — Venv bootstrap and dependency installation supported.
- **Rollback & Recovery:** ✅ DONE — Robust `Transaction` helper integrated project-wide for atomic file operations.

### Phase 3: Test Strategy & Structured CI (Status & progress)

- **Comprehensive Testing (in-progress):** Library management commands (`rename`, `move`, `remove`) are now transactional and include project-wide CMake reference updates. Highlights:
  - **`rename`:** updates source files, headers, and CMake target references atomically under the repository `Transaction` helper; supports `--dry-run` preview for automation and safety.
  - **`move`:** moves the library directory under `libs/` and the corresponding test directory under `tests/unit/`, and updates `libs/CMakeLists.txt` and `tests/unit/CMakeLists.txt` registrations. If the destination basename differs from the original library name, the tool can perform token replacement inside moved files and update CMake target references to keep targets consistent.
  - **`remove`:** detaches the library from the CMake registration and, when `--delete` is supplied, deletes files from disk. After deletion the tool prunes empty parent directories under `libs/` and `tests/unit/` to avoid orphaned folders.
  - **Safety & UX:** All operations run under the `Transaction` helper for backup and rollback on error. For destructive `--delete` removals the CLI prompts for confirmation unless `--yes` is provided; use `--dry-run` to preview actions without applying them. Programmatic calls (tests/scripts) bypass interactive prompts.
- **Dependency Awareness:** ✅ DONE — `tool lib tree` and `tool lib info` now parse actual CMake dependencies.
- **Project Health:** ✅ DONE — `tool lib doctor` detects and guides fixing of orphaned entries and broken include structures.
- **Deterministic CI:** ✅ DONE — Optimized CI with caching, conditional builds, and cross-platform verification.
- **App Scaffolding:** In-progress — `tool sol target add` implemented for automated app creation.

### Phase 4: Safety, Hardening & Sanitizers

- **Sanitizer Profiles:** `tool build --profile sanitized` support.
- **Security Audit:** Integrate CVE scanning (e.g., `osv-scanner`).

### Phase 5: Performance & Optimization

- **Performance Tracking:** Benchmark history and regression tracking.
- **Performance Budget:** Threshold checks for performance regressions.

### Phase 6: Ecosystem & UI

- **TUI as Wrapper:** Integrate `scripts/tui.py` with the central `tool` dispatcher.
- **Live Doc Server:** `tool doc serve` to serve documentation locally.

### Phase 7: Configuration & State Management

- **`tool.toml`:** Central configuration file.
- **State Persistence:** `.tool/state.json` for session history.
- **Lock Files:** Deterministic dependency management via lock files.

---

## 📜 Governance

- **SemVer:** Semantic versioning for CLI and templates.
- **LTS Support:** Maintain both Latest and LTS release streams.

---

## 💡 Strategic Recommendations

1. **Keep Template Logic Minimal:** Keep template files small; implement complex logic in Python.
2. **Atomic Operations:** Ensure file mutations support rollback.
3. **Static Analysis Integration:** Integrate `clang-tidy --fix` into the `check` command to improve quality.

## Long-Term Vision

Once everything is completed, only Python scripts will remain; there will be no pre-existing CMake or C++ source files. All CMakeLists.txt and .cpp / .h files will be generated entirely by the scripts. In this way, the project structure will be programmatically defined and managed by the scripts, increasing flexibility while minimizing manual intervention.

### Final Goal: Cargo + Cookiecutter + Bazel + IaC (Infrastructure as Code) Pattern

The entire C++ project structure should be generated by scripts,
and those scripts should manage the full lifecycle of the project.
