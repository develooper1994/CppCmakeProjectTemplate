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

### Phase 2: Distribution & Template Engine (Next)

- **Jinja2 Migration:** Move f-string based templates to Jinja2.
- **Packaging:** Distribute `tool` as a pip-installable package.
- **Bootstrap (`tool setup`):** Automated installation of dependencies and Python environment.
- **Rollback & Recovery:** Add state rollback for failed file operations.

Progress updates:

- **Jinja2 Migration:** Planned — migration to Jinja2 templates is scoped and scheduled; work not yet started.
- **Packaging:** In-progress — extension packaging hardened and `.vsix` produced; next step is packaging the `tool` CLI as a pip-installable package and publishing to PyPI.
- **Bootstrap (`tool setup`):** Done — added `scripts/setup_python_env.py` (cross-platform venv creation) and CI workflow `.github/workflows/create_envs.yml` to create environments on Ubuntu/macOS/Windows.
- **Rollback & Recovery:** Partial — added `backup_session()` and safer session persistence; further atomic rollback for file mutations is planned.

### Phase 3: Test Strategy & Structured CI

- **Comprehensive Testing:** Unit and fixture tests for CLI tooling.
- **Deterministic CI:** Frozen environments for reproducible builds.
- **Template Smoke Tests:** Automated template validation across compilers.

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


---

## **Recent Work (2026-03-28)**

- **Session persistence:** Shared session helpers (`load_session`, `save_session`, `backup_session`) available at `scripts/core/utils/common.py`; both `tool.py` and `tui.py` use the shared `.session.json`.
- **Verification harness:** Added `scripts/verify_full.py` which automates build, test, extension packaging and library flows; logs to `build_logs/verify.log`.
- **Cross-platform venv helper & CI:** Added `scripts/setup_python_env.py` and `.github/workflows/create_envs.yml` to create environments on Ubuntu/macOS/Windows.
- **Extension packaging & release:** Hardened extension packaging flow; ensured `.vsix` packaging works via `vsce`/`npx` and added minimal `build` script in `extension/package.json`. Published a test patch and created tag `v1.03`.
- **Library tooling improvements:** Refactored `core.libpkg` exports; `tool lib` uses the modular helpers for create/export/remove flows and writes debug logs to `build_logs/`.
- **Performance micro-optimizations (safe):**
	- Added a small JSON-read cache and helpers (`json_read_cached`, `json_cache_clear`) in `scripts/core/utils/common.py`.
	- Replaced repeated `json.loads()` reads for presets and `.fetch_deps.json` with cached readers in `scripts/core/commands/sol.py` and `scripts/core/commands/build.py`.
	- Implemented an incremental template sync in `scripts/core/commands/build.py` to avoid full remove/copy cycles and skip unchanged files.

All changes were tested via `scripts/verify_full.py` and `ctest` — no syntax or runtime issues were found. See `build_logs/verify.log` for details.
