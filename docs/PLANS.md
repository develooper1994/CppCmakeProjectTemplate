# CppCmakeProjectTemplate — Plans & Capabilities

This document lists the project's current capabilities and remaining backlog items.

---

## ✅ Current Capabilities (Completed)

### Unified CLI & Tooling Framework

- **Unified CLI (`tool.py`):** A single entrypoint that manages all commands (`build`, `lib`, `sol`) and dynamic plugins (`plugins/`).
- **Modern Directory Layout:** Clear separation between infrastructure (`core/utils`), command logic (`core/commands`) and plugins (`plugins/`).
- **Structured Logging:** Standard log levels and persistent log storage.
- **Standardized Results:** Commands return a `CLIResult` and support `--json` for automation.
- **Clean Environment:** Legacy scripts consolidated into a single professional interface.
- **Shared Session Persistence:** `load_session()`, `save_session()`, `backup_session()` used by both `tool.py` and `tui.py` via `.session.json`.
- **Verification Harness:** `scripts/verify_full.py` automates build/test/extension and library flows.
- **Python Environment Automation:** `scripts/setup_python_env.py` creates cross-platform virtual environments.
- **Extension Packaging Hardened:** Reliable `.vsix` production under `extension/`.
- **Library Packaging Helpers:** `core.libpkg` refactored to a modular helper surface.

### Build System

- **Modern CMake (3.25+):** Target-based structure with no global flags.
- **Preset Matrix:** 34 ready presets for Linux, Windows, macOS and Embedded (ARM).
- **MSVC Consistency:** Automatic selection of `/MT` or `/MD` when appropriate.
- **Per-Target BuildInfo:** Per-target versioning and git metadata support.
- **Dynamic Feature Flags:** Feature toggles controlled at build time.
- **Build Configuration Summary:** `build/build_config.json` emitted at build time with profile, sanitizers, preset, and generated sources.
- **CMakePresets.json Generator:** `tool presets generate` reads `tool.toml [presets]` and generates the full preset matrix. Supports per-dimension filters, constraint matrix, auto-backup, `--dry-run`.
- **`tool presets list` / `validate`:** List visible presets and validate via `cmake --list-presets`.

### Distribution & Template Engine

- **Jinja2 Migration:** Integrated for `libpkg` and `sol` subsystems with fallback behavior.
- **Bootstrap (`tool setup`):** Checks mandatory/optional system dependencies. `--install`/`--do-install` via apt/brew/dnf/pacman auto-detection. Creates/populates Python venv.
- **Rollback & Recovery:** Robust `Transaction` helper for atomic file operations.

### Test Strategy & CI

- **Comprehensive Testing:** Library management commands (`rename`, `move`, `remove`) are transactional with CMake reference updates. `--dry-run` preview, `--yes` for automation, `Transaction` rollback.
- **Dependency Awareness:** `tool lib tree` and `tool lib info` parse actual CMake dependencies.
- **Project Health:** `tool lib doctor` detects orphaned entries and broken include structures.
- **Deterministic CI:** Optimized CI with caching, conditional builds, cross-platform verification.
- **App Scaffolding:** `tool sol target add` for automated app creation.

### Safety, Hardening & Sanitizers

- **Multi-Tiered Security Profiles:** `normal` → `strict` → `hardened` → `extreme` (Rust-like safety).
- **Granular Sanitizer Selection:** `tool build --sanitizers asan ubsan` or `--sanitizers all`.
- **Per-Target Overrides:** `-D<TARGET_NAME>_ENABLE_HARDENING=ON/OFF`, `-D<TARGET_NAME>_ENABLE_ASAN=ON/OFF`.
- **Dynamic Static Analysis:** `.clang-tidy` dynamically generated based on active profile via Jinja2.
- **Security Audit:** `tool security scan` with OSV-Scanner + Cppcheck, tiered policy enforcement.
- **CVE Scanning:** Integrated `osv-scanner` for dependency vulnerability auditing.
- **Fuzz Testing:** libFuzzer harness, AFL++ CI (nightly long-run), seed-corpus management, crash triage.
- **Static Analysis:** `clang-tidy --fix` automation (`tool format tidy-fix`) and CI job.
- **Security Hardening:** `cmake/Hardening.cmake` — stack canaries, PIE, RELRO, CFI, FORTIFY_SOURCE, MSVC equivalents.
- **Workflow Consolidation:** Reusable CI workflow (`.github/workflows/reusable-ci.yml`).

### Granular Control

All per-script and per-target toggles implemented as `-D` CMake options and CLI flags:

- **Build / CMake / Tooling**: `--profile`, `--sanitizers`, `--preset`, per-target `-D<TARGET>_ENABLE_*`.
- **Fuzzing**: `-DENABLE_FUZZING`, `-DENABLE_AFL`, `--timeout-ms`, `--target`/`--corpus-root`.
- **Security Scan**: `--install`, `--format`, `--fail-on-severity`, `--suppressions`.
- **clang-tidy / format**: `format tidy-fix`, `--dry-run`, `--apply`, `--checks`.
- **CI / Automation**: `--skip-ci`, `--ci-mode`, `--report-artifact`, `--retain-days`.
- **Release & Packaging**: `--install`, `--dry-run`, `--signing-key`, `--publish`.

### Performance & Optimization

- **Performance Tracking:** `tool perf track` saves size+build-time baseline to `build_logs/perf_baseline.json`.
- **Performance Budget:** `tool perf check-budget` compares current build vs baseline, fails CI on regressions.
- **Profile-Guided Optimization (PGO):** `cmake/PGO.cmake` — two-phase PGO (generate/use) for GCC, Clang, MSVC. BOLT post-link optimization via `ENABLE_BOLT=ON`.
- **Link-Time Optimization (LTO):** `cmake/LTO.cmake` — CheckIPOSupported, thin LTO for Clang, per-target support.
- **Build Caching:** `cmake/BuildCache.cmake` — auto-detects ccache/sccache.
- **Build Visualization:** `tool perf graph` — CMake dependency graph via `cmake --graphviz` with optional `dot` rendering.
- **Cross-Compilation:** 3 new toolchains + 5 new CMake presets (embedded/aarch64).
- **Embedded Targets:** `cmake/EmbeddedUtils.cmake` — 4 functions for embedded binary outputs, map files, memory usage, linker scripts.
- **Code Size Analysis:** `tool perf size` — analyzes all built binaries with JSON report.
- **Build Time Analysis:** `tool perf build-time` — Ninja `.ninja_log` analysis with JSON report.
- **Compiler Explorer:** `tool perf godbolt` — compiles via Godbolt REST API. `tool perf vec` for local vectorization.
- **Performance Profiling:** `tool perf stat` — wraps `perf stat` (with `time -v` fallback). `tool perf record` for flame graphs.
- **Automated Perf Regression Detection:** `.github/workflows/perf_regression.yml` — 10% size / 25% time thresholds with artifact upload.
- **Performance Annotations:** `bench_greet.cpp` — Sieve, Monte Carlo, matrix multiply, Newton-Raphson, Fibonacci benchmarks with cross-platform macros.
- **Runtime Performance Metrics:** `perf::ScopedTimer` and `perf::ThroughputCounter` — zero-dependency, header-inline.
- **Memory Usage Analysis:** `tool perf valgrind [--vg-tool memcheck|massif]` with XML/massif output.
- **Concurrency Analysis:** `tool perf concurrency` — Valgrind helgrind/DRD with XML report. TSan via `--sanitizers tsan`.
- **Cache Optimization:** `tool perf stat` — reports cache-misses/cache-references counters.
- **Vectorization Analysis:** `tool perf vec` — compiler vectorization remarks. CMake: `-DENABLE_VEC_REPORT=ON`.
- **Auto-Parallelization:** `cmake/OpenMP.cmake` — `enable_openmp()`, `enable_openmp_simd()`, `enable_auto_parallelization()`. GCC/Clang/MSVC support.
- **Zero-Cost Abstractions:** `[[likely]]`/`[[unlikely]]`, `ATTR_HOT`/`ATTR_COLD`/`ATTR_PURE`/`ATTR_NOINLINE` macros.
- **Binary Size Delta Tracking:** `tool perf size-diff` — compares `.text`/`.data`/`.bss` against baseline.
- **Auto-Tuner:** `tool perf autotune` — hill/grid/random/anneal strategies with speed/size/instructions oracles.

### Ecosystem & UI

- **TUI as Wrapper:** `tool tui` dispatches to `scripts/tui.py`.
- **Live Doc Server:** `tool doc serve [--port N] [--open]` — serves `docs/` via Python `http.server`. `tool doc build` supports mkdocs/sphinx.

### Configuration & State Management

- **`tool.toml`:** 9 sections (`tool`, `build`, `perf`, `security`, `lib`, `doc`, `release`, `hooks`, `embedded`). Read by `config_loader.py` via `tomllib`/`tomli`. CLI args override.
- **State Persistence:** `.session.json` shared by `tool.py` and `tui.py`. `tool session save/load/set` subcommands.

### GUI, GPU & Tooling

- **Qt5/Qt6 Support:** `cmake/Qt.cmake` — auto-detects Qt6 (Qt5 fallback). `target_link_qt(<target> [QML] ...)`. AUTOMOC/AUTOUIC/AUTORCC. Cross-compile aware.
- **CUDA / GPU Offloading:** `cmake/CUDA.cmake` — WSL-aware nvcc detection, `enable_cuda_support()`, `target_add_cuda()`, `set_cuda_architectures()`. Clang-as-CUDA fallback.
- **CUDA-Version-Aware C++ Standard:** `cuda_compatible_cxx_standard()` — maps CUDA toolkit version to max device-code C++ standard.
- **AMD HIP Support:** `cmake/HIP.cmake` — `enable_hip_support()`, `target_add_hip()`, `set_hip_architectures()`. Auto-detects GPU via `rocm_agent_enumerator`. **Caveat:** untestable without ROCm SDK.
- **Auto-Detect C++ Standard:** `cmake/CxxStandard.cmake` — probes compiler features at configure time. Three-strategy detection pipeline (feature check → compile probe → version heuristic).

### C++ Modernity & DX

- **C++20 Modules:** `cmake/CxxModules.cmake` — `enable_cxx_modules(<target>)`, `CXX_SCAN_FOR_MODULES ON` (CMake 3.28+). `tool lib add --modules` generates `.cppm` stubs.
- **Stdlib-Aware C++ Detection:** Three-strategy pipeline (feature check, compile probe, version heuristic). Supports C++98/03 through C++23.
- **IWYU:** `cmake/IWYU.cmake` + `tool format iwyu [--target <lib>] [--fix]`.
- **Compiler Explorer (Godbolt):** `tool perf godbolt` — POSTs to Godbolt API, `--save`, `--json`.
- **Binary Reproducibility:** `cmake/Reproducibility.cmake` — deterministic builds with `SOURCE_DATE_EPOCH`, `ar -D`, file-prefix-map.

### Ecosystem & Integration

- **Conan 2.0 Profile Generation:** `tool deps conan-profile generate` — maps `tool.toml [presets]` to Conan 2 profiles.
- **Docker Build:** `tool build docker` — builds inside container.
- **Package Publishing:** `tool release publish --to github|conan|vcpkg` and `tool release unpublish --to github|conan|vcpkg`.
- **Cross-Compile Sysroot Management:** `tool sol sysroot add <arch>` — downloads/installs sysroots, writes `sysroots/registry.json`.
- **LibFuzzer Native Integration:** `cmake/Fuzzing.cmake` — `enable_libfuzzer(<target>)`.
- **Lock Files:** `tool deps lock [--managers vcpkg|conan|pip]` — generates lock files. `tool deps verify` checks staleness.

### Versioning & Release

Single source-of-truth `VERSION` file at repository root (`<major>.<middle>.<minor>+<revision>`).

- `scripts/release.py`: CLI helper for `bump`, `set`, `set-revision`, `tag`, `publish`, `unpublish`.
- `tool release`: wrapper via unified CLI.
- `CMakeLists.txt`: reads `VERSION` for `project(... VERSION ...)`.
- CI: `.github/workflows/release.yml` derives revision from `run_number`.

### Git Leak Detection (gitleaks)

- **Pre-Commit Hook:** `.pre-commit-config.yaml` with gitleaks v8.18.4.
- **CI Integration:** `.github/workflows/gitleaks.yml` — push/PR/weekly scans with SARIF upload.
- **Custom Rules:** `.gitleaks.toml` — 3 custom rules + project-specific allowlists.

---

## 🔜 Not Completed (V2 / Future Backlog)

### Hot Reloading _(V2 / Long-term)_

C++ hot-reloading (LLVM JIT / cr.h) requires significant runtime scaffolding and OS-specific shared library reload. ccache + unity builds already minimize rebuild latency. Deferred until V2.

### Automated Performance Tuning _(V2 / Long-term)_

PGO + BOLT (already implemented) cover the primary automated tuning strategies. Auto-tuning frameworks (e.g., OpenTuner, Halide scheduling) are out of scope for V1.

### Intel SYCL Support _(V2 / Long-term)_

Architecture is in place (see `cmake/CUDA.cmake` and `cmake/HIP.cmake` patterns). Add `cmake/SYCL.cmake` when a concrete Intel GPU target exists.

### Apple Metal Support _(V2 / Long-term)_

Architecture is in place. Add `cmake/Metal.cmake` (via Metal-cpp or similar) when macOS GPU compute targets are needed.

### Memory Pooling & Custom Allocators _(Future / User-Land)_

Template does not prescribe allocators by design. `tool perf valgrind --vg-tool massif` profiles heap usage. Users may link `mimalloc` or `jemalloc` via vcpkg/conan. CMake helper `target_use_allocator()` could be added per user request.

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
