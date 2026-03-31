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

### Phase 3: Test Strategy & Structured CI (Status & progress) - Completed

- **Comprehensive Testing (in-progress):** ✅ DONE - Library management commands (`rename`, `move`, `remove`) are now transactional and include project-wide CMake reference updates. Highlights:
  - **`rename`:** updates source files, headers, and CMake target references atomically under the repository `Transaction` helper; supports `--dry-run` preview for automation and safety.
  - **`move`:** moves the library directory under `libs/` and the corresponding test directory under `tests/unit/`, and updates `libs/CMakeLists.txt` and `tests/unit/CMakeLists.txt` registrations. If the destination basename differs from the original library name, the tool can perform token replacement inside moved files and update CMake target references to keep targets consistent.
  - **`remove`:** detaches the library from the CMake registration and, when `--delete` is supplied, deletes files from disk. After deletion the tool prunes empty parent directories under `libs/` and `tests/unit/` to avoid orphaned folders.
  - **Safety & UX:** All operations run under the `Transaction` helper for backup and rollback on error. For destructive `--delete` removals the CLI prompts for confirmation unless `--yes` is provided; use `--dry-run` to preview actions without applying them. Programmatic calls (tests/scripts) bypass interactive prompts.
- **Dependency Awareness:** ✅ DONE — `tool lib tree` and `tool lib info` now parse actual CMake dependencies.
- **Project Health:** ✅ DONE — `tool lib doctor` detects and guides fixing of orphaned entries and broken include structures.
- **Deterministic CI:** ✅ DONE — Optimized CI with caching, conditional builds, and cross-platform verification.
- **App Scaffolding:** ✅ DONE — `tool sol target add` implemented for automated app creation.

### Phase 4: Safety, Hardening & Sanitizers (Rust-like C++ Safety)

- **Multi-Tiered Security Profiles:** ✅ DONE — Implementation of progressive safety levels.
  - **`normal`**: Base warnings (`-Wall -Wextra`).
  - **`strict`**: Aggressive warnings (`-Wconversion`, `-Wshadow`, etc.).
  - **`hardened`**: `strict` + `-Werror` + `-fstack-protector-strong` + `_FORTIFY_SOURCE=2` + `-fPIE`.
  - **`extreme`**: Full "Rust-like" safety. `hardened` + `uninitialized-init` + `-fno-exceptions` + `-fno-rtti` + Full RELRO + `-pie`.
- **Granular Sanitizer Selection:** ✅ DONE — Separated from profiles, allowing combinations with any safety level.
  - Usage: `tool build --sanitizers asan ubsan` or `tool build --sanitizers all`.
- **Granular Control (Per-Target Overrides):** ✅ DONE — Any security or sanitizer feature can be enabled/disabled per library or application.
  - Usage: Pass `-D<TARGET_NAME>_ENABLE_HARDENING=ON/OFF` or `-D<TARGET_NAME>_ENABLE_ASAN=ON/OFF`.
- **Security Audit:** In-progress — Integrate CVE scanning (e.g., `osv-scanner`) for dependencies.
- **Fuzz Testing:** Integrate fuzzing tools (e.g., `afl++`, `libFuzzer`).
- **Static Analysis:** Integrate additional static analysis tools (e.g., `clang-tidy --fix`).
- **Security Hardening:** Implement features like stack canaries, PIE, RELRO, and control flow integrity (CFI) in build presets.

### Phase 5: Performance & Optimization

- **Performance Tracking:** Benchmark history and regression tracking.
- **Performance Budget:** Threshold checks for performance regressions.
- **Profile-Guided Optimization (PGO):** Support for PGO builds and workflows.
- **Link-Time Optimization (LTO):** Support for LTO builds and workflows.
- **Build Caching:** Integrate ccache or similar for faster incremental builds.
- **Build Visualization:** Generate build graphs and dependency visualizations.
- **Hot Reloading:** Explore hot-reloading capabilities for faster development iterations.
- **Cross-Compilation:** Enhance support for cross-compilation targets and workflows.
- **Embedded Targets:** Add presets and tooling for embedded development (e.g., ARM Cortex-M).
- **Code Size Analysis:** Tools for analyzing and optimizing binary size.
- **Build Time Analysis:** Tools for analyzing and optimizing build times.
- **Compiler Explorer Integration:** Integrate with Compiler Explorer for easy access to assembly output and compiler insights.
- **Performance Profiling Integration:** Integrate with profiling tools (e.g., `perf`, `VTune`, `Instruments`) for streamlined performance analysis.
- **Automated Performance Regression Detection:** Integrate performance benchmarks into CI to automatically detect regressions.
- **Documentation of Performance Best Practices:** Create documentation and guidelines for writing high-performance C++ code within the project.
- **Performance Annotations:** Support for annotating code with performance hints (e.g., `[[likely]]`, `[[unlikely]]`, `[[nodiscard]]`) and enforcing their correct usage.
- **Compiler-Specific Optimizations:** Provide utilities for applying compiler-specific optimizations (e.g., `__attribute__((hot))`, `__declspec(noinline)`) in a cross-platform manner.
- **Runtime Performance Metrics:** Integrate runtime performance metrics collection and reporting for applications built with the project.
- **Automated Performance Tuning:** Explore integration with tools that can automatically suggest performance improvements based on code analysis and profiling data.
- **Performance-Focused Code Reviews:** Establish guidelines and checklists for performance-focused code reviews to ensure that performance considerations are consistently addressed in pull requests.
- **Memory Usage Analysis:** Tools for analyzing and optimizing memory usage, including heap profiling and leak detection.
- **Concurrency Analysis:** Tools for analyzing and optimizing concurrent code, including thread sanitizers and race condition detectors.
- **Cache Optimization:** Tools and guidelines for optimizing cache usage and reducing cache misses.
- **Vectorization Analysis:** Tools for analyzing and optimizing vectorization opportunities in code.
- **Auto-Parallelization:** Explore tools and techniques for automatically parallelizing code where appropriate.
- **GPU Offloading:** Explore support for GPU offloading (e.g., CUDA, OpenCL) for performance-critical code sections.
- **Memory Pooling & Custom Allocators:** Support for memory pooling and custom allocators to reduce fragmentation and improve performance.
- **Zero-Cost Abstractions:** Guidelines and tools for writing zero-cost abstractions in C++ to achieve high performance without sacrificing code clarity.

### Phase 6: Ecosystem & UI

- **TUI as Wrapper:** Integrate `scripts/tui.py` with the central `tool` dispatcher.
- **Live Doc Server:** `tool doc serve` to serve documentation locally.

### Phase 7: Configuration & State Management

- **`tool.toml`:** Central configuration file.
- **State Persistence:** `.tool/state.json` for session history.

## Versioning & Release Workflow

We standardize on a single source-of-truth `VERSION` file at the repository root.
The format is: `<major>.<middle>.<minor>+<revision>` (e.g. `1.2.3+45`). The
`+<revision>` part is optional and used for build metadata (CI run number or
build counter).

Key elements:

- `VERSION` (root): canonical version string used by `scripts/release.py` and
  consumed by `scripts/tool.py` via `GlobalConfig.VERSION` at runtime.
- `scripts/release.py`: CLI helper to `bump`, `set`, `set-revision`, and
  `tag`.
- `tool release`: wrapper that delegates to `scripts/release.py` so releases can
  be run via the unified CLI (e.g. `python3 scripts/tool.py release bump minor`).
- `CMakeLists.txt`: reads `VERSION` and uses the three-part base version for the
  `project(... VERSION ...)` invocation; build metadata (`+revision`) is not
  passed to CMake project but is available to packaging and docs.
- CI: `.github/workflows/release.yml` derives a revision (GitHub `run_number`) and
  runs `scripts/release.py` on tag push or via `workflow_dispatch` (dry-run by
  default; set `apply: true` on dispatch to perform commit/tag/push).

Workflow summary:

1. Developer runs `python3 scripts/tool.py release bump patch` (or `bump minor/major`).
2. `scripts/release.py` updates `VERSION`, synchronizes `pyproject.toml`,
   `extension/package.json`, and top-level `CMakeLists.txt`, then commits.
3. Optionally `scripts/release.py tag --push` will create and push `v<major>.<middle>.<minor>`.
4. CI (`release.yml`) can be used to set the `+revision` metadata automatically
   and optionally publish artifacts.

This approach centralizes version management, reduces accidental drift, and
provides both manual CLI and CI-driven release paths.

- **Lock Files:** Deterministic dependency management via lock files.

## Git leak detection (gitleaks)

- **Pre-Commit Hook:** Implement a Git pre-commit hook that scans for sensitive information (e.g., API keys, secrets) using regex patterns. The hook should block commits that contain potential leaks and provide feedback to the developer.
- **CI Integration:** Integrate gitleaks into the CI pipeline to automatically scan all commits and pull requests for sensitive information. This ensures that any potential leaks are caught before they are merged into the main branch.
- **Custom Rules:** Define custom gitleaks rules specific to the project’s context (e.g., patterns for internal API keys, database credentials) to enhance detection accuracy.
- **Reporting & Alerts:** Configure gitleaks to generate reports and send alerts (e.g., email, Slack) when potential leaks are detected, enabling prompt response and remediation.

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
