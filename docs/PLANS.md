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
- **Shared Session Persistence:** `load_session()`, `save_session()`, `backup_session()` used by both `tool.py` and `tui.py` via the `[session]` section in `tool.toml`.
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
- **Cross-Compilation:** 3 new toolchains + 5 new CMake presets (embedded/aarch64). MSVC ARM64 (`arm64`/`aarch64` → `ARM64` Visual Studio arch). Platform-aware skip rules: embedded targets gcc-only + static-only, musl static-only, zig gcc-base-only, arm64 MSVC-only. Full musl expansion: aarch64-linux-musl + zig variants, vcpkg overlay triplets (`triplets/`), Conan musl profiles, CI nightly musl workflow.
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
- **Optional Allocator Backends:** `cmake/Allocators.cmake` — `target_use_allocator()` and `project_apply_allocator()` for mimalloc, jemalloc, tcmalloc. CLI: `tool build --allocator {default|mimalloc|jemalloc|tcmalloc}`. Per-target and global override (`ENABLE_ALLOCATOR_OVERRIDE_ALL`). All executables, tests, and benchmarks wired. Zero application code changes required. Conan/vcpkg integration with conditional dependencies. Preset generator allocator dimension (`tool.toml [presets] allocators`). FetchContent fallback for mimalloc (`ALLOCATOR_FETCHCONTENT=ON`). `std::pmr` pool utilities via `cmake/PoolAllocator.h`.

### Ecosystem & UI

- **TUI as Wrapper:** `tool tui` dispatches to `scripts/tui.py`.
- **Live Doc Server:** `tool doc serve [--port N] [--open]` — serves `docs/` via Python `http.server`. `tool doc build` supports mkdocs/sphinx.

### Configuration & State Management

- **`tool.toml`:** 9 sections (`tool`, `build`, `perf`, `security`, `lib`, `doc`, `release`, `hooks`, `embedded`). Read by `config_loader.py` via `tomllib`/`tomli`. CLI args override.
- **`tool.toml` Session:** Runtime state stored in `[session]` section of `tool.toml` (replaces `.session.json`). `tool session save/load/set` subcommands.

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

### Memory Pooling & Custom Allocators _(Complete)_

**Completed (Tier 1 — Backend Wiring):** `cmake/Allocators.cmake` with mimalloc/jemalloc/tcmalloc support, CLI `--allocator` flag, per-target and global override, all targets wired.

**Completed (Tier 2 — Dependency & Preset Integration):**

- **Dependency manager integration:** Conan `allocator` option (`-o allocator=mimalloc|jemalloc|tcmalloc`) auto-pulls the correct library. vcpkg `features` (`mimalloc`, `jemalloc`) for feature-gated dependencies.
- **Allocator preset variants:** `tool.toml [presets] allocators` dimension. Generates presets like `gcc-release-static-x86_64-mimalloc` with `ENABLE_ALLOCATOR` and `ENABLE_ALLOCATOR_OVERRIDE_ALL` cache variables pre-set. CLI: `tool presets generate --allocator mimalloc,jemalloc`.
- **FetchContent fallback:** `ALLOCATOR_FETCHCONTENT=ON` auto-downloads mimalloc from upstream when not found via system/Conan/vcpkg. jemalloc/tcmalloc require system install (autotools builds).
- **Improved discovery:** `find_package(CONFIG)` tried first for all backends (vcpkg/Conan targets), then `find_library`, then FetchContent (mimalloc only).
- **Pool APIs:** `cmake/PoolAllocator.h` — header-only `std::pmr`-based wrappers: `StackPool<N>` (monotonic buffer), `UnsyncPool` (unsynchronized pool), `SyncPool` (synchronized pool). Zero dependencies, C++17.
- **Diagnostics:** `tool perf valgrind --vg-tool massif` for heap profiling.

### Static Analysis & Cppcheck Acceleration _(Complete)_

**Completed (Core):** Parallel jobs (`--cppcheck-jobs`), tiered profiles (`--cppcheck-checks full|minimal`), path scoping (`--cppcheck-paths`), `--fast` shorthand.

**Completed (CI & Caching):**

- **CI tiering:** PR runs use `--fast` (minimal checks), nightly schedule (`cron: 0 3 * * *`) runs full scan.
- **Cache-aware workflow:** `--cppcheck-build-dir` persists analysis of unchanged TUs; CI caches via `actions/cache`.
- **Suppression hygiene:** Centralized `.cppcheck-suppressions.txt` auto-loaded by default; `--suppressions FILE` override preserved.

### musl / Static Build Expansion _(Complete)_

**Completed (Tier 1 — Toolchains & Docker):** x86_64 musl toolchain (GCC-based), Zig cc + musl toolchain, Alpine Dockerfile, Zig-musl Dockerfile, Docker file consolidation, preset generator wiring with skip rules.

**Completed (Tier 2 — ARM64 & Ecosystem Integration):**

- **aarch64-linux-musl:** ARM64 fully static builds via musl cross-toolchain (`cmake/toolchains/aarch64-linux-musl.cmake`). Requires `musl-cross-make` or Alpine Docker with QEMU.
- **aarch64-linux-musl-zig:** ARM64 via Zig cc (`cmake/toolchains/aarch64-linux-musl-zig.cmake`). Zero-install cross-compilation.
- **CI nightly musl job:** `.github/workflows/musl_nightly.yml` — Alpine native x86_64, Zig x86_64, Zig aarch64 cross-compile with QEMU smoke-test. Schedule (04:00 UTC) + manual dispatch.
- **Conan musl profiles:** `_MUSL_ARCH_MAP` in deps.py maps musl arch names to canonical Conan arches. Hard skip rules for musl-dynamic / zig-nonGCC. Toolchain file injection via `tools.cmake.cmaketoolchain:user_toolchain`.
- **vcpkg musl triplets:** `triplets/` overlay directory with 4 custom triplets (`x86_64-linux-musl`, `aarch64-linux-musl`, `x86_64-linux-musl-zig`, `aarch64-linux-musl-zig`). All static, chainload respective toolchain files. Usage: `vcpkg install --overlay-triplets=triplets`.
- **Zig toolchain consistency:** All zig-musl toolchains now have search policy (`CMAKE_FIND_ROOT_PATH_MODE_*`) and sanitizer disabling.

### GPU & Compute — SYCL + Metal _(Complete)_

**Completed (Infrastructure):** SYCL and Metal CMake modules following the same pattern as CUDA and HIP (caveat header, option guard, find toolkit, target helper, auto-run at module level). All modules are untestable without their respective SDKs.

- **Intel SYCL / DPC++:** `cmake/SYCL.cmake` — `ENABLE_SYCL` option, `_sycl_find_compiler()` (icpx / clang++ -fsycl), `_sycl_detect_devices()` (sycl-ls), `enable_sycl_support()`, `target_add_sycl()`, `set_sycl_targets()` (-fsycl-targets=spir64|spir64_gen|nvidia_gpu_sm_80|amd_gpu_gfx90a).
- **Apple Metal:** `cmake/Metal.cmake` — `ENABLE_METAL` option (macOS-only), `_metal_find_sdk()` (xcrun), `_metal_find_cpp_headers()` (metal-cpp), `enable_metal_support()`, `target_add_metal()` (Metal + MetalKit + Foundation frameworks), `target_compile_metal_shaders()` (.metal → .air → .metallib pipeline).
- **CMakeLists.txt wiring:** `include(SYCL)` and `include(Metal)` added after `include(HIP)`.
- **Preset skip rules:** SYCL skipped for MSVC (no -fsycl), Metal skipped on non-Apple. `tool.toml` skip_combinations updated.
- **Configuration:** `tool.toml [gpu]` section with commented `sycl_targets` and `metal_sdk` entries.

### Automated Performance Tuning V2 _(Complete)_

**Completed (V2 Additions):** Evidence-based preset promotion, hardware-aware recommendations, and multi-run noise reduction.

- **`tool perf promote`:** Reads `autotune_results.json`, extracts winning flags, writes a `*-perf-tuned-*` configure preset into `CMakePresets.json`. `--min-improvement PCT` threshold gate, `--base-preset` override, `--dry-run` preview.
- **`tool perf hw-recommend`:** Reads `/proc/cpuinfo` (Linux) or `sysctl` (macOS) to detect CPU vendor, model, ISA extensions. Recommends `-march=native`, `-mtune=native`, and specific ISA flags (`-mavx2`, `-mfma`, `-mavx512f`, etc.). Table + `--json` output.
- **`tool perf autotune --repeat N`:** Runs the oracle N times per trial and uses the median score. Reduces measurement noise for speed/instructions oracles. Size oracle skips repeats (deterministic).

---

## 🔜 Not Completed (V2 / Future Backlog)

### Performance _(V2)_

- **Hot Reloading:** C++ hot-reloading (LLVM JIT / cr.h) requires significant runtime scaffolding and OS-specific shared library reload. ccache + unity builds already minimize rebuild latency.

### Internal Tooling _(V2 / Structural)_

- **Internal Tooling Refactor Program:** Large-scale refactor planned after stabilization milestones.
  - Motivation: some script files are too long, responsibilities overlap, code duplication exists.
  - Refactor principle: split by clear domain ownership, not by micro-fragmentation.
  - Target: command facade → execution/service → shared utility → plugin boundary.
  - Execution: phased vertical slices (domain-by-domain), each with full regression checks.
  - Guardrails: no "big bang" rewrites; each phase must remain buildable/testable and reversible.

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
