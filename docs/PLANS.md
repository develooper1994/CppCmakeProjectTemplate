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
- **musl libc / Fully Static Builds:** `cmake/toolchains/x86_64-linux-musl.cmake` — produces zero-dependency statically linked binaries. Auto-detects musl-cross-make or `musl-gcc` wrapper. `docker/Dockerfile.alpine` for native musl C++ builds. Preset generator wires `gcc-*-static-x86_64-linux-musl` presets with automatic dynamic-linkage skip. Sanitizers disabled (incompatible with musl). Optional `-static-pie` via `MUSL_STATIC_PIE=ON`.
- **Zig cc + musl:** `cmake/toolchains/x86_64-linux-musl-zig.cmake` — Zig ships with musl libc built-in; no separate musl toolchain or Alpine Docker required. Creates wrapper scripts for `zig cc` / `zig c++`. `docker/Dockerfile.zig-musl` for containerized builds.
- **Docker Consolidation:** All Dockerfiles organized under `docker/` — `Dockerfile` (Ubuntu dev), `Dockerfile.alpine` (musl native), `Dockerfile.zig-musl` (Zig cc + musl).

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
- **Cppcheck Acceleration:** `--cppcheck-jobs N` (parallel, auto-detect CPU count), `--cppcheck-checks {full|minimal}` (tiered profiles), `--cppcheck-paths` (path scoping for incremental scans), `--fast` shorthand.
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
- **Cross-Compilation:** 3 new toolchains + 5 new CMake presets (embedded/aarch64). MSVC ARM64 (`arm64`/`aarch64` → `ARM64` Visual Studio arch). Platform-aware skip rules: embedded targets gcc-only + static-only, musl static-only, zig gcc-base-only, arm64 MSVC-only.
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
- **Optional Allocator Backends:** `cmake/Allocators.cmake` — `target_use_allocator()` and `project_apply_allocator()` for mimalloc, jemalloc, tcmalloc. CLI: `tool build --allocator {default|mimalloc|jemalloc|tcmalloc}`. Per-target and global override (`ENABLE_ALLOCATOR_OVERRIDE_ALL`). All executables, tests, and benchmarks wired. Zero application code changes required.

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
- **Docker Build:** `tool build docker` — builds inside container. Dockerfiles consolidated under `docker/`.
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

PGO + BOLT (already implemented) cover the primary automated tuning strategies for V1. V2 expands this into a closed-loop system:

- **Phase 1 (safe defaults):** Keep current `tool perf autotune` strategies (hill/grid/random/anneal) as optional non-blocking advisors.
- **Phase 2 (evidence-based presets):** Promote only repeatedly winning flag sets into optional presets (for example `*-perf-tuned-*`).
- **Phase 3 (CI budget gates):** Feed baseline and tuned runs into `tool perf check-budget` with policy thresholds.
- **Phase 4 (nightly exploration):** Run wider candidate sweeps at night, keep PR pipelines deterministic and fast.
- **Phase 5 (portfolio tuning):** Maintain separate tuning profiles for speed-focused and size-focused outputs.

Scope remains practical: no mandatory heavy external tuning framework for V1/V1.x; integrations are incremental and reversible.

### Intel SYCL Support _(V2 / Long-term)_

Architecture is in place (see `cmake/CUDA.cmake` and `cmake/HIP.cmake` patterns). Add `cmake/SYCL.cmake` when a concrete Intel GPU target exists.

### Apple Metal Support _(V2 / Long-term)_

Architecture is in place. Add `cmake/Metal.cmake` (via Metal-cpp or similar) when macOS GPU compute targets are needed.

### Memory Pooling & Custom Allocators _(Partially Complete)_

**Completed (Tier 1 — Backend Wiring):** `cmake/Allocators.cmake` with mimalloc/jemalloc/tcmalloc support, CLI `--allocator` flag, per-target and global override, all targets wired.

Remaining:

- **Dependency manager integration:** Conan/vcpkg conditional `requires` for allocator libraries.
- **Allocator preset variants:** Optional presets like `gcc-release-mimalloc-x86_64`.
- **Pool APIs:** `std::pmr`-based memory resources and optional Boost.Pool adapters (separate category, not global malloc replacement).
- **Dependency policy:** Boost.Pool support requires explicit optional Boost enablement.
- **Diagnostics:** Continue relying on `tool perf valgrind --vg-tool massif`.

### Static Analysis & Cppcheck Acceleration _(Complete)_

**Completed (Core):** Parallel jobs (`--cppcheck-jobs`), tiered profiles (`--cppcheck-checks full|minimal`), path scoping (`--cppcheck-paths`), `--fast` shorthand.

**Completed (CI & Caching):**

- **CI tiering:** PR runs use `--fast` (minimal checks), nightly schedule (`cron: 0 3 * * *`) runs full scan.
- **Cache-aware workflow:** `--cppcheck-build-dir` persists analysis of unchanged TUs; CI caches via `actions/cache`.
- **Suppression hygiene:** Centralized `.cppcheck-suppressions.txt` auto-loaded by default; `--suppressions FILE` override preserved.

### Internal Tooling Refactor Program _(V2 / Structural)_

Large-scale refactor is planned after stabilization milestones, with safety gates at each step.

- **Motivation:** some script files are too long, responsibilities overlap, and code duplication exists.
- **Refactor principle:** split by clear domain ownership, not by artificial micro-fragmentation.
- **Target architecture:**
  - command facade layer
  - execution/service layer
  - shared utility layer
  - plugin boundary with stable contracts
- **Execution style:** phased vertical slices (domain-by-domain), each with full regression checks.
- **Anti-duplication plan:** extract repeated argument parsing, runner orchestration, and reporting helpers.
- **Guardrails:** no broad "big bang" rewrites; each phase must remain buildable/testable and reversible.
- **Completion criteria:** shorter cohesive modules, lower churn hotspots, and preserved CLI compatibility.

### musl / Static Build Expansion _(Partially Complete)_

**Completed:** x86_64 musl toolchain (GCC-based), Zig cc + musl toolchain, Alpine Dockerfile, Zig-musl Dockerfile, Docker file consolidation, preset generator wiring with skip rules.

Remaining:

- **aarch64-linux-musl:** ARM64 fully static builds via musl cross-toolchain.
- **aarch64-linux-musl-zig:** ARM64 via Zig cc (`zig cc -target aarch64-linux-musl`).
- **CI nightly musl job:** Catch static-linking regressions in scheduled builds.
- **Conan/vcpkg musl profiles:** Package manager integration for musl-targeted dependency resolution.

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
