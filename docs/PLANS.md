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
