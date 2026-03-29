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

### Phase 2: Distribution & Template Engine (Status & progress)

- **Jinja2 Migration:** Partial — a Jinja2-based POC was implemented and integrated for the `libpkg` scaffolding subsystem. Many templates were added under `scripts/core/libpkg/templates/`, and code paths in `scripts/core/libpkg` were updated to prefer Jinja rendering while preserving the f-string fallback when Jinja2 is not available.
- **Packaging:** In-progress — extension packaging was hardened and a `.vsix` was produced; the `tool` CLI packaging metadata was added to `pyproject.toml`. Next step: publish `tool` as a pip package (PyPI) after tests and dependency pinning.
- **Bootstrap (`tool setup`):** Done — `scripts/setup_python_env.py` and `scripts/plugins/setup.py` were extended to support venv bootstrap and dependency installation.
- **Rollback & Recovery:** Done (core) — a `Transaction` helper for atomic file operations was implemented at `scripts/core/utils/fileops.py`, integrated into `create_library`, and covered by unit and edge-case tests.

Recent work (committed):

- Added Jinja2 helper and many `.jinja2` templates for library scaffolding (`scripts/core/libpkg/templates/`) with fallback behavior.
- Implemented transactional file-ops helper `Transaction` and integrated it into `create_library` for atomic writes and rollback.
- Added comprehensive unit tests for `Transaction` (normal and edge-case scenarios) and template integration tests; tests run locally: `17 passed`.
- Optimized CI workflow: caching for `pip` and `ccache`, improved cache keys, `paths-filter` to detect C/C++ changes, and conditional matrix builds so heavy C++ builds run only when relevant files change. Changes were committed and pushed on branch `ci/optimize-cache-and-tests`.

Recommended next steps (short-term):

- Perform a repository-wide sweep to identify remaining f-string template usages and convert only the file-generation paths that benefit from Jinja2 (leave runtime/log messages as f-strings).
- Add unit tests for `create_library` failure modes (simulate mid-write exceptions) and expand Transaction tests for cross-device rename with real move semantics where possible.
- Finalize `pyproject.toml` packaging metadata, pin runtime dependencies, and publish the `tool` CLI to PyPI (use a test PyPI release first).
- Integrate the Python tests into the project CI as a required check and enable PR gating for the optimized CI workflow.

Recommendations (longer-term):

- Add cache keys tied to lockfiles (if you adopt Poetry/Pipfile) or lockfile hashes for reproducible pip caches.
- Use `gh` or automation to create the PR from the `ci/optimize-cache-and-tests` branch (branch already pushed).
- Add CI matrix caching for prebuilt dependencies (vcpkg/Conan) and consider incremental build artifacts between jobs.

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

## Long work

Herşey tamamlandıktan sonra scriptler cmake ve c++ dosyaları olmadan sadece python dosyaları kalacak. CMakeLists.txt ve .cpp/.h dosyaları tamamen scriptler tarafından oluşturulacak. Böylece proje yapısı tamamen scriptlere programatik olarak tanımlanmış ve yönetiliyor olacak. Bu, projenin esnekliğini artıracak ve manuel müdahaleyi azaltacaktır.
