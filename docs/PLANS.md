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

- **Build Configuration Summary:** The build system now emits `build/build_config.json` at build time. This JSON contains the active `--profile` (for example `normal`, `hardened`, `extreme`), selected sanitizers, the chosen CMake preset/toolchain, and a list of headers or sources generated at configure/generation time. This artifact is intended for CI traceability, debugging, and reproducing the exact configuration used to produce an artifact.

### Quality & CI/CD

- **Testing:** Support for GoogleTest, Catch2, Boost.Test and QTest.
- **Quality Gates:** ASan, UBSan, TSan, Clang-Tidy and Cppcheck integration.
- **CI/CD:** GitHub Actions multi-platform matrix builds.

---

## 🚀 Roadmap

### Phase 1: Foundation & Unified CLI — ✅ DONE

- **Modular Dispatcher:** ✅ DONE
- **Command Contracts:** ✅ DONE
- **Structured Logging:** ✅ DONE
- **Plugin Discovery:** ✅ DONE
- **Migration & Cleanup:** ✅ DONE (legacy scripts consolidated)
- **Refactoring & Core Migration:** ✅ DONE (command logic moved under `core/commands`)

### Phase 2: Distribution & Template Engine — ✅ DONE

- **Jinja2 Migration:** ✅ DONE — Integrated for `libpkg` and `sol` subsystems with fallback behavior.
- **Packaging:** ✅ DONE — Extension packaging hardened; `tool` metadata added to `pyproject.toml`.
- **Bootstrap (`tool setup`):** ✅ DONE — `tool setup [--install] [--do-install] [--all] [--env] [--install-env] [--recreate]`. Checks mandatory (cmake, ninja, git, python3) and optional (lcov, doxygen, clang, clang-tidy, cppcheck, osv-scanner, valgrind, ccache, gitleaks) system dependencies. `--install` shows the install command; `--do-install` actually runs it via apt/brew/dnf/pacman auto-detection. Creates/populates Python venv.
- **Rollback & Recovery:** ✅ DONE — Robust `Transaction` helper integrated project-wide for atomic file operations.

### Phase 3: Test Strategy & Structured CI (Status & progress) - ✅ DONE

- **Comprehensive Testing (in-progress):** ✅ DONE - Library management commands (`rename`, `move`, `remove`) are now transactional and include project-wide CMake reference updates. Highlights:
  - **`rename`:** updates source files, headers, and CMake target references atomically under the repository `Transaction` helper; supports `--dry-run` preview for automation and safety.
  - **`move`:** moves the library directory under `libs/` and the corresponding test directory under `tests/unit/`, and updates `libs/CMakeLists.txt` and `tests/unit/CMakeLists.txt` registrations. If the destination basename differs from the original library name, the tool can perform token replacement inside moved files and update CMake target references to keep targets consistent.
  - **`remove`:** detaches the library from the CMake registration and, when `--delete` is supplied, deletes files from disk. After deletion the tool prunes empty parent directories under `libs/` and `tests/unit/` to avoid orphaned folders.
  - **Safety & UX:** All operations run under the `Transaction` helper for backup and rollback on error. For destructive `--delete` removals the CLI prompts for confirmation unless `--yes` is provided; use `--dry-run` to preview actions without applying them. Programmatic calls (tests/scripts) bypass interactive prompts.
- **Dependency Awareness:** ✅ DONE — `tool lib tree` and `tool lib info` now parse actual CMake dependencies.
- **Project Health:** ✅ DONE — `tool lib doctor` detects and guides fixing of orphaned entries and broken include structures.
- **Deterministic CI:** ✅ DONE — Optimized CI with caching, conditional builds, and cross-platform verification.
- **App Scaffolding:** ✅ DONE — `tool sol target add` implemented for automated app creation.

### Phase 4: Safety, Hardening & Sanitizers (Rust-like C++ Safety) — ✅ DONE

- **Multi-Tiered Security Profiles:** ✅ DONE — Implementation of progressive safety levels.
  - **`normal`**: Base warnings (`-Wall -Wextra`).
  - **`strict`**: Aggressive warnings (`-Wconversion`, `-Wshadow`, etc.).
  - **`hardened`**: `strict` + `-Werror` + `-fstack-protector-strong` + `_FORTIFY_SOURCE=2` + `-fPIE`.
  - **`extreme`**: Full "Rust-like" safety. `hardened` + `uninitialized-init` + `-fno-exceptions` + `-fno-rtti` + Full RELRO + `-pie`.
- **Granular Sanitizer Selection:** ✅ DONE — Separated from profiles, allowing combinations with any safety level.
  - Usage: `tool build --sanitizers asan ubsan` or `tool build --sanitizers all`.
- **Granular Control (Per-Target Overrides):** ✅ DONE — Any security or sanitizer feature can be enabled/disabled per library or application.
  - Usage: Pass `-D<TARGET_NAME>_ENABLE_HARDENING=ON/OFF` or `-D<TARGET_NAME>_ENABLE_ASAN=ON/OFF`.

#### Planned Actions (priority order)

  1. Consolidate CI workflows and reduce duplication — ✅ DONE (composite actions and initial refactor applied).
  2. Add `--install` to top-level scripts and provide a unified install helper — ✅ DONE (`core.utils.common` now exposes optional provisioning and scripts accept `--install`).
  3. Add `.cmake-format` and a CI formatting job (auto-fix candidate generation) — ✅ DONE (`.cmake-format` and CI job added).
  4. Complete AFL++ integration: enable `afl-clang-fast` builds in CI, seed-corpus upload/retention, and long-run nightly fuzz jobs — ✅ DONE (AFL++ build + nightly long-run workflow added; seed corpus present and artifact retention implemented).
  5. Expand analyzer granularity: document and expose per-script and per-target analyzer toggles — ✅ DONE (Granular Control expanded and toggles exposed in `core` and CMake modules).
  6. Add per-library `docs/` and `LICENSE` files (automatically generated by `tool lib` in the future) — ✅ DONE (each library under `libs/` includes `docs/README.md` and `LICENSE`).
  7. Automate `clang-tidy --fix` PR flow: generate candidate fixes, open PRs, and gate re-enablement of strict analyzers behind review — ✅ DONE (`tool format tidy-fix` + CI job added; PR automation is configured to produce diff artifacts and auto-PR is scaffolded).

  8. Granular Control: expose per-target and per-script toggles in `core.utils.common` and CMake modules — ✅ DONE (global `--install`, per-target `-D<TGT>_ENABLE_*` and analyzer toggles implemented).

  Status update (2026-04-01): The Phase‑4 planned items listed above have been implemented and validated in this feature branch.

- Seed-corpus triage & minimization pipeline: ✅ DONE — implemented in `scripts/fuzz/triage.py` and `scripts/fuzz/findings_collector.py`. The corpus manager and AFL findings collector support `afl-cmin`/`afl-tmin` where available and provide safe fallbacks.
- `clang-tidy --fix` PR automation: ✅ DONE — implemented as `scripts/ci/tidy_pr_bot.py` and CI job scaffolding to generate candidate fix branches and PRs (uses `tool format tidy-fix` under the hood).
- Workflow consolidation: ✅ DONE — reusable workflow added at `.github/workflows/reusable-ci.yml` and key callers (nightly AFL long‑run) updated to use it. This significantly reduces duplication across CI jobs.

  Notes: Remaining follow-ups are operational tuning and incremental improvements (artifact retention policy, alerting thresholds, and coverage of additional fuzz targets). These are tracked in the repository issue tracker.

- **Dynamic Static Analysis:** ✅ DONE — `.clang-tidy` is now dynamically generated based on the active profile (`normal`, `strict`, `hardened`, `extreme`) using Jinja2 templates.
  - `hardened/extreme` profiles enforce `WarningsAsErrors: "*"`.
  - `extreme` profile enables additional aggressive safety checks by removing suppressions.
- **Security Audit Command:** ✅ DONE — New `tool security scan` command for CVE and static security analysis.
- **CVE Scanning:** ✅ DONE — Integrated `osv-scanner` for dependency vulnerability auditing.
- **Security Audit:** ✅ DONE — `tool security scan` with OSV-Scanner + Cppcheck, `ci_security_policy.py` for tiered policy enforcement (CRITICAL→fail, HIGH→warn), and `security_scan.yml` CI workflow with artifact upload.
- **Fuzz Testing:** ✅ DONE — libFuzzer harness, AFL++ CI (nightly long-run) and seed-corpus support added.
- **Static Analysis:** ✅ DONE — `clang-tidy --fix` automation (`tool format tidy-fix`) and CI job added.
- **Security Hardening:** ✅ DONE — `cmake/Hardening.cmake` implements stack canaries (`-fstack-protector-strong`), stack clash protection, PIE (`-fPIE`/`-pie`), RELRO (`-Wl,-z,relro,-z,now`), CFI (`-fcf-protection`), `_FORTIFY_SOURCE=2/3`, per-target overrides, and MSVC equivalents (ControlFlowGuard, /GS, /sdl, Qspectre).

Notes & recent decisions (implemented / important constraints):

- **Build-time generated headers:** Some headers are produced during configure/generation by CMake or project scripts. These generated files are recorded in `build/build_config.json` and are treated as "generated sources" by the analyzer policy to avoid false-positives originating from generated code. This analyzer scoping does not remove hardening flags from production targets — it only narrows which files will fail CI due to stylistic analyzer rules. To include generated headers in analysis, enable per-target analysis flags (for example `-D<target>_ANALYZE_GENERATED=ON`) or run `tool format tidy-fix` to apply automatic fixes before re-enabling strict analyzer policies.

- **Preserving Hardening Semantics:** Hardening compiler/linker flags (`-fstack-protector-strong`, `_FORTIFY_SOURCE=2`, PIE/RELRO, etc.) remain applied to production libraries and executables by default. Analyzer exclusions are narrowly scoped (third-party dependencies, generated headers, and test/fuzz harness targets) to avoid CI failures on non-actionable warnings. If you prefer stricter enforcement, enable per-target analyzer checks or use the `extreme` profile which tightens checks further.

- **Fuzz Testing (current status):** ✅ Complete — libFuzzer + AFL++ integration, seed-corpus management (`scripts/fuzz/triage.py`), nightly long-run CI jobs, and automated crash triage (`scripts/fuzz/findings_collector.py`) are all implemented.

- **clang-tidy --fix automation:** A `tool format tidy-fix` helper and a CI job (`.github/workflows/clang_tidy_fix.yml`) were added to run `clang-tidy -fix` and produce the resulting diff/artifact for review. This facilitates safe re-enabling of analyzers by producing fix-candidates that can be reviewed and merged incrementally.

- **Security-scan CI reporting & policy:** ✅ Complete — `tool security scan` integrated with CI artifact upload, tiered policy enforcement via `ci_security_policy.py` (CRITICAL→exit 2, HIGH→exit 1), and `security_scan.yml` workflow with checkout, Go setup, and policy evaluation steps.

### Granular Control — Expanded ✅ DONE

All per-script and per-target toggles are now implemented and available as `-D` CMake options for targets and as CLI flags for scripts.

- **Build / CMake / Tooling**: ✅ `--profile` (`normal|strict|hardened|extreme`), `--sanitizers` (asan,ubsan,tsan), `--preset`, `-D<TARGET>_ENABLE_HARDENING`, `-D<TARGET>_ANALYZE_GENERATED`, `-D<TARGET>_ENABLE_ASAN`.
- **Fuzzing**: ✅ `-DENABLE_FUZZING`, `-DENABLE_AFL`, `--timeout-ms` (triage.py), `--target` / `--corpus-root` (corpus_manager.py).
- **Security Scan**: ✅ `--install`, `--format json|text`, `--fail-on-severity` (CRITICAL/HIGH/MEDIUM/LOW), `--suppressions <file>`.
- **clang-tidy / format**: ✅ `format tidy-fix`, `--dry-run`, `--apply`, `--checks <pattern>`.
- **CI / Automation**: ✅ `--skip-ci` (local debug), `--ci-mode` (smoke|full|nightly), `--report-artifact` (path), `--retain-days` (artifact retention policy) — all exposed in `tool.py` global flags and `GlobalConfig`.
- **Release & Packaging**: ✅ `--install`, `--dry-run`, `--signing-key` (GPG tag signing), `--publish` (release publish subcommand).

### Phase 5: Performance & Optimization — ✅ DONE

- **Performance Tracking:** ✅ DONE — `tool perf track` saves a size+build-time baseline to `build_logs/perf_baseline.json` (13+ artifacts tracked).
- **Performance Budget:** ✅ DONE — `tool perf check-budget [--size-threshold N] [--time-threshold N]` compares current build vs baseline, fails CI on regressions.
- **Profile-Guided Optimization (PGO):** ✅ DONE — `cmake/PGO.cmake` supports two-phase PGO (generate/use) for GCC, Clang, and MSVC. CLI: `tool build --pgo generate|use --pgo-dir <dir>`. Per-target override: `-D<TARGET>_ENABLE_PGO=ON/OFF`. **BOLT post-link optimization** also supported via `ENABLE_BOLT=ON` (adds `bolt-instrument-<target>` / `bolt-optimize-<target>` CMake targets; requires `llvm-bolt ≥ 14`). CLI: `tool build --bolt`.
- **Link-Time Optimization (LTO):** ✅ DONE — `cmake/LTO.cmake` with `CheckIPOSupported`, per-target support, thin LTO for Clang. CLI: `tool build --lto`. Per-target override: `-D<TARGET>_ENABLE_LTO=ON/OFF`.
- **Build Caching:** ✅ DONE — `cmake/BuildCache.cmake` auto-detects and configures ccache/sccache as compiler launcher. `-DENABLE_CCACHE=ON` (default). Override: `-DCACHE_PROGRAM=/path/to/ccache`.
- **Build Visualization:** ✅ DONE — `tool perf graph [--render] [--format svg|png|pdf]` generates CMake dependency graph via `cmake --graphviz` with optional `dot` rendering.
- **Hot Reloading:** _(V2 / Long-term)_ — C++ hot-reloading (LLVM JIT / cr.h) requires significant runtime scaffolding and OS-specific shared library reload. ccache + unity builds already minimize rebuild latency. Deferred until V2.
- **Cross-Compilation:** ✅ DONE — 3 new toolchains (`aarch64-linux-gnu`, `arm-cortex-m0`, `arm-cortex-m7`) + 5 new CMake presets (`embedded-cortex-m0/m4/m7`, `gcc-debug/release-static-aarch64`).
- **Embedded Targets:** ✅ DONE — `cmake/EmbeddedUtils.cmake` rewritten with 4 functions: `add_embedded_binary_outputs`, `add_embedded_map_file`, `embedded_print_memory_usage`, `target_set_linker_script`. 3 new toolchains + 3 new embedded presets.
- **Code Size Analysis:** ✅ DONE — `tool perf size` analyzes all built binaries/libraries with human-readable output and JSON report. Auto-detects active preset build directory. Uses `size` (berkeley format) for section breakdown.
- **Build Time Analysis:** ✅ DONE — `tool perf build-time` analyzes Ninja `.ninja_log` for per-target build times, or runs a timed rebuild with JSON report output.
- **Compiler Explorer Integration:** _(Phase 8 — Nice-to-have)_ — `tool perf vec` already shows vectorization info. Full Compiler Explorer (godbolt.org API) integration via `tool perf godbolt --source <file>` could stream asm to terminal. Interim: use `objdump -d` or `llvm-objdump` locally.
- **Performance Profiling Integration:** ✅ DONE — `tool perf stat` wraps Linux `perf stat` (with `time -v` fallback) for CPU/cache counter profiling; `tool perf record` flag generates `perf.data` for flame graphs.
- **Automated Performance Regression Detection:** ✅ DONE — `.github/workflows/perf_regression.yml` runs on every push/PR: builds release preset, restores cached baseline, runs `tool perf check-budget` (10% size / 25% time thresholds), uploads size+build-time reports as artifacts. Weekly schedule refreshes the baseline.
- **Documentation of Performance Best Practices:** ✅ DONE — `docs/PERFORMANCE.md` created with comprehensive guide covering ccache/sccache, LTO, thin LTO, PGO two-phase workflow, `perf size`, `perf build-time`, CMake configure summary table, and recommended release profile. `docs/BUILD_SETTINGS.md` and `docs/BUILD_INFO.md` also updated.
- **Performance Annotations:** ✅ DONE — `libs/dummy_lib/benchmarks/bench_greet.cpp` shows real compute-heavy benchmarks: Sieve of Eratosthenes (cache-friendly), Monte Carlo π (branch-heavy), matrix multiply naïve vs. cache-tiled (cache locality), Newton-Raphson √ (FPU-bound convergence), recursive Fibonacci (recursion depth, LTO gain). Cross-platform `ATTR_HOT`/`ATTR_NOINLINE` macros, `SetBytesProcessed`/`SetItemsProcessed` throughput reporting. Build with `--preset gcc-release-static-x86_64 -DENABLE_BENCHMARKS=ON` to compare optimization levels.
- **Compiler-Specific Optimizations:** ✅ DONE — `ATTR_HOT`/`ATTR_NOINLINE` macros in `bench_greet.cpp` with GCC/Clang/MSVC guards. Integrated into benchmark targets via `cmake/Benchmark.cmake`. BOLT workflow documented in `cmake/PGO.cmake` (LLVM ≥ 14).
- **Runtime Performance Metrics:** ✅ DONE — `apps/demo_app/src/main.cpp` demonstrates `perf::ScopedTimer` (µs wall-clock RAII) and `perf::ThroughputCounter` (ops/s) using `std::chrono::high_resolution_clock`. Zero-dependency, header-inline, cross-platform.
- **Automated Performance Tuning:** _(V2 / Long-term)_ — PGO + BOLT (already implemented) cover the primary automated tuning strategies. Auto-tuning frameworks (e.g., OpenTuner, Halide scheduling) are out of scope for V1.
- **Performance-Focused Code Reviews:** ✅ DONE — `docs/PERFORMANCE.md` contains a comprehensive guide covering ccache, LTO, PGO, vectorization, `perf stat`, flame graphs, and benchmark best practices.
- **Memory Usage Analysis:** ✅ DONE — `tool perf valgrind [--vg-tool memcheck|massif] [--target <binary>]` runs Valgrind and saves XML/massif output. `ms_print` summary displayed for massif.
- **Concurrency Analysis:** ✅ DONE — `tool perf concurrency --binary <bin> [--tool helgrind|drd]` runs Valgrind helgrind/DRD with XML report. `tool build --sanitizers tsan` provides compile-time TSan (preferred for CI).
- **Cache Optimization:** ✅ DONE — `tool perf stat` reports `cache-misses` and `cache-references` counters via `perf stat -e`. Build caching (ccache/sccache) is handled by `cmake/BuildCache.cmake`.
- **Vectorization Analysis:** ✅ DONE — `tool perf vec --source <file>` emits compiler vectorization remarks (`-Rpass=loop-vectorize` on Clang, `-fopt-info-vec` on GCC) and saves a report. CMake option: `-DENABLE_VEC_REPORT=ON` applies flags project-wide.
- **Auto-Parallelization:** ✅ DONE — `cmake/OpenMP.cmake` provides `enable_openmp()`, `enable_openmp_simd()`, `enable_auto_parallelization()` per-target helpers. GCC: `-floop-parallelize-all -ftree-parallelize-loops=N` (N=CPU count). Clang: Polly `-mllvm -polly -polly-parallel` with libgomp linkage (or -fopenmp-simd fallback). MSVC: `/Qpar`. Global options: `-DENABLE_OPENMP=ON`, `-DENABLE_OPENMP_SIMD=ON`, `-DENABLE_AUTO_PARALLEL=ON`. CLI: `tool build --openmp | --openmp-simd | --auto-parallel`.
- **GPU Offloading:** _(Phase 8 — Near-term)_ — CMake has built-in CUDA support (`enable_language(CUDA)`). A CUDA preset + `cmake/CUDA.cmake` module can be added. Roadmapped for Phase 8 when a concrete GPU target exists. Metal (Apple), HIP (AMD), SYCL (Intel) also viable paths.
- **Memory Pooling & Custom Allocators:** _(Future / User-Land)_ — Template does not prescribe allocators by design. `tool perf valgrind --vg-tool massif` profiles heap usage. Users may link `mimalloc` or `jemalloc` via vcpkg/conan. CMake helper `target_use_allocator()` could be added per user request.
- **Zero-Cost Abstractions:** ✅ DONE — `libs/dummy_lib/benchmarks/bench_greet.cpp` demonstrates `[[likely]]`/`[[unlikely]]`, `ATTR_HOT`/`ATTR_COLD`/`ATTR_PURE`/`ATTR_NOINLINE` cross-platform macros. `docs/PERFORMANCE.md` covers the guidelines.

### Phase 6: Ecosystem & UI — ✅ DONE

- **TUI as Wrapper:** ✅ DONE — `tool tui` dispatches to `scripts/tui.py`. `tui/` app already wired via CORE_COMMANDS `"tui": "tui"`.
- **Live Doc Server:** ✅ DONE — `tool doc serve [--port N] [--open]` serves `docs/` via Python `http.server`. `tool doc list` shows all 15 documents. `tool doc build` supports mkdocs/sphinx.

### Phase 7: Configuration & State Management — ✅ DONE

- **`tool.toml`:** ✅ DONE — `tool.toml` at project root contains 9 sections (`[tool]`, `[build]`, `[perf]`, `[security]`, `[lib]`, `[doc]`, `[release]`, `[hooks]`, `[embedded]`). Read by `scripts/core/utils/config_loader.py` via `tomllib` (Python 3.11+) with `tomli` fallback and minimal built-in parser. Values flow into `GlobalConfig` at dispatcher startup. CLI args always take precedence.
- **State Persistence:** ✅ DONE — `.session.json` at project root stores session history (last preset, verbose/json/yes/dry_run flags, default command). Managed by `scripts/core/commands/session.py` via `load_session()`, `save_session()`, `backup_session()` in `core.utils.common`. Both `tool.py` and `tui.py` share this single file – `tool session save/load/set` subcommands expose it via CLI.

### Phase 8: GUI, GPU & Tooling Evolution — ✅ DONE

#### Framework Support

- **Qt5/Qt6 Support:** ✅ DONE — `cmake/Qt.cmake` auto-detects Qt6 (falls back to Qt5). Provides `target_link_qt(<target> [QML] [NETWORK] [MULTIMEDIA] [OPENGL] [SVG])` helper: sets AUTOMOC/AUTOUIC/AUTORCC, links all requested components, defines `FEATURE_QT=1` and `QT_VERSION_MAJOR`. Global option: `-DENABLE_QT=ON [-DENABLE_QML=ON]`. CLI: `tool build --qt [--qml]`. Cross-compile (AArch64): pass `-DQT_HOST_PATH=` + `-DCMAKE_PREFIX_PATH=`. Bare-metal targets (Cortex-M*) forcibly disable Qt. `apps/gui_app/CMakeLists.txt` updated to use `target_link_qt()` and `apply_openmp_defaults()`.
- **OpenMP & Auto-Parallelization:** ✅ DONE — see Phase 5.

#### GPU & Heterogeneous Computing

- **CUDA / GPU Offloading:** ✅ DONE — `cmake/CUDA.cmake`: WSL-aware nvcc detection (`/usr/bin`, `/usr/local/cuda/bin`, `/usr/lib/cuda/bin`). `enable_cuda_support()`, `target_add_cuda(<target> [SEPARABLE])`, `set_cuda_architectures(<target> native|all-major|<list>)`. `ENABLE_CUDA=ON` option. `CMAKE_CUDA_ARCHITECTURES=native` (auto GPU detect). Clang-as-CUDA fallback (`CUDA_COMPILER=clang`). `CUDA_SEPARABLE_COMPILATION` global toggle. CLI: `tool build --cuda`.
- **CUDA-Version-Aware C++ Standard:** ✅ DONE — `cuda_compatible_cxx_standard()` in `cmake/CxxStandard.cmake` maps CUDA toolkit version → maximum device-code C++ standard (CUDA <9→C++11, 9–10→C++14, 11–12.1→C++17, ≥12.2→C++20). `CMAKE_CUDA_STANDARD` auto-set from toolkit; warning emitted when host C++ std exceeds device limit. Per-target override: `set_target_properties(<t> PROPERTIES CUDA_STANDARD 20)`.
- **AMD HIP / Intel SYCL / Apple Metal:** _(V2 / Long-term)_ — Architecture is in place; add `cmake/HIP.cmake`, `cmake/SYCL.cmake` when concrete targets exist.

#### Compiler & C++ Standard Intelligence

- **Auto-Detect C++ Standard:** ✅ DONE — `cmake/CxxStandard.cmake` probes `CMAKE_CXX_COMPILE_FEATURES` at configure time and sets `CMAKE_CXX_STANDARD` to the highest standard the compiler supports (C++23 → C++20 → C++17 → …). No-op when the user sets an explicit value via CLI or preset. Exposed as `CXX_STANDARD_DETECTED` (non-cache) for downstream logic. See `docs/BUILD_SETTINGS.md § C++ Standard Auto-Detection`. CLI: status logged as `[CxxStd] Auto-detected C++ standard: C++XX`.

#### Preset Generation (Python-driven, key V1 goal)

- **CMakePresets.json Generator:** ✅ DONE — `tool presets generate` reads `tool.toml [presets]` (compilers, build_types, linkages, arches) and generates the **entire** `CMakePresets.json` (hidden bases + configurePresets + buildPresets + testPresets). Supports per-dimension filters: `--compiler`, `--build-type`, `--linkage`, `--arch`. Constraint matrix enforced (CUDA → static linkage, etc.; extensible via `skip_combinations` patterns). Auto-backup `CMakePresets.json.bak` before overwrite. `--dry-run` and `--no-backup` flags. `cuda_architectures = "native"` from `tool.toml [presets]`. Validated: `cmake --list-presets` → 12/12 presets OK.
- **`tool presets list`:** ✅ DONE — lists visible presets with display names.
- **`tool presets validate`:** ✅ DONE — runs `cmake --list-presets` and reports status.

#### Tooling Quality

- **Compiler Explorer (Godbolt) Integration:** _(Phase 9 — Roadmapped)_ — `tool perf godbolt --source <file>` streams compiled asm via godbolt.org API. `tool perf vec` covers local vectorization analysis in the interim.

### Phase 9: C++ Modernity, Tooling DX & Ecosystem — 🔜 Planned

Priority-ordered backlog. Items marked _(quick)_ are low-effort and high-value.

#### Quick Wins

- **`lib upgrade-std`** _(quick, ✅ IMPL)_ — `tool lib upgrade-std <lib> --std 20 [--dry-run]` sets C++ standard for one library's CMakeLists.txt. Scoped to `libs/<lib>/`. Complements `sol upgrade-std` which operates project-wide.
- **`sol upgrade-std`** _(quick, ✅ IMPL)_ — `tool sol upgrade-std --std 20 [--target <lib>]` traverses `libs/` and `apps/` CMakeLists.txt, bumps `CXX_STANDARD` to the requested value. `--target <lib>` scopes the change to one library. Dry-run by default.
- **`sol cmake-version`** _(quick, ✅ IMPL)_ — `tool sol cmake-version detect` prints the installed CMake version and the project's `cmake_minimum_required` value. `tool sol cmake-version set <VERSION> [--dry-run]` updates `cmake_minimum_required(VERSION …)` in every `CMakeLists.txt` (skipping `external/`, `build/`, `_deps/`).
- **`.clangd` Auto-Generation** _(quick, ✅ IMPL)_ — `tool sol clangd [--dry-run]` locates `compile_commands.json` and emits a `.clangd` file with the correct `CompilationDatabase`, `InlayHints`, and `Diagnostics` sections. Ensures clangd picks up the active preset without manual editor config.
- **Binary Size Delta Tracking** _(quick, ✅ IMPL)_ — `tool perf size-diff [--base <file>] [--fail-on-growth <bytes>] [--json]` reads the saved `perf_baseline.json` (from `tool perf track`) and compares `.text` / `.data` / `.bss` sections against the current build. `--fail-on-growth` is opt-in; CI does not block by default. Writes `build_logs/size_report.json`.

#### Language & Compiler Evolution

- ✅ **IMPL** **C++20 Modules support** _(medium)_ — `cmake/CxxModules.cmake`: `enable_cxx_modules(<target>)` guarded by `CXX_STANDARD >= 20`; sets `CXX_SCAN_FOR_MODULES ON` (CMake 3.28+); GCC: `-fmodules-ts`; Clang: native. `tool lib add --modules` generates a `.cppm` module-interface+implementation unit stub, skips classic `include/`, registers `FILE_SET CXX_MODULES` in CMakeLists.txt, generates a module-import test. Requires CMake ≥ 3.28, Clang ≥ 16 or GCC ≥ 13.
- **Stdlib-Aware C++ Detection** _(quick, ✅ IMPL)_ — `cmake/CxxStandard.cmake` extended with a three-strategy detection pipeline. **Strategy A** (fast, no compile): checks `CMAKE_CXX_COMPILE_FEATURES` for `cxx_std_XX` — used as a diagnostic, not a hard gate. **Strategy B** (authoritative): `_cxx_compile_probe()` compiles a canary source with `-std=c++XX`; validates both language support AND stdlib header availability; runs regardless of Strategy A result, catching cross-toolchains where CMake under-populates the feature list. **Strategy C** (last resort): `_compiler_version_max_std()` compiler-version heuristic table (GCC/Clang/MSVC/Intel); emits a `WARNING`; only activated if all compile probes fail. Supported range: **C++98/03 · 11 · 14 · 17 · 20 · 23** (C++03 maps to `98`; each std has a tailored canary source). Cache key: `CXX_COMPILE_PROBE_<std>_OK`.

#### Developer Experience (DX)

- **IWYU (Include What You Use)** _(medium)_ — `cmake/IWYU.cmake` wrapper: `find_program(iwyu ...)` + `set_target_properties(<t> PROPERTIES CXX_INCLUDE_WHAT_YOU_USE ${iwyu})`. CLI: `tool format iwyu [--target <lib>] [--fix]`. CI job reports unnecessary includes as annotations.
- **Compiler Explorer (Godbolt) Integration** _(medium)_ — `tool perf godbolt --source <file> [--compiler gcc-13] [--flags -O2]` uploads a snippet via the Compiler Explorer REST API and streams the assembly diff to the terminal. Pair with `tool perf vec` for local analysis.
- **Binary Reproducibility** _(medium)_ — Enforce `-ffile-prefix-map=$(pwd)=.`, `SOURCE_DATE_EPOCH` from `git log -1 --format=%ct`, and deterministic archive creation (`ar -D`). `tool build --reproducible` preset toggle. Validate with `diffoscope`. Documented in `docs/BUILDING.md`.

#### Performance & Auto-Tuning

- **Auto-Tuner** _(medium, ✅ IMPL)_ — `tool perf autotune [--strategy hill|grid|random|anneal] [--oracle speed|size|instructions] [--rounds N] [--list-tools] [--T-init T] [--T-alpha α] [--json]` sweeps a compiler-flag search space defined in `tool.toml [autotuner]`. **Oracles:** `speed` (Google Benchmark `cpu_time` sum, default); `size` (`size --format=berkeley` .text+.data bytes, uses `size_flag_candidates`; `bloaty` fallback); `instructions` (`perf stat -e instructions`; `valgrind --tool=callgrind` fallback; falls back to `speed` if neither present). **Strategies:** `hill` (flip one flag per round, keep if improvement); `grid` (cartesian product up to `--rounds`); `random` (sample random combinations); `anneal` (simulated annealing, escapes local optima). `--list-tools` prints tool availability without running trials. Tool detection via `_detect_available_tools()` (probes nm, size, objdump, bloaty, perf, valgrind, hyperfine, gprof). Output: `build_logs/autotune_results.json` + terminal table. Pairs with `libs/dummy_lib/benchmarks/bench_greet.cpp`.

#### Ecosystem & Integration

- **Conan 2.0 Profile Generation from Presets** _(medium)_ — `tool deps conan-profile generate` maps `tool.toml [presets]` matrix to Conan 2 profiles (`[settings] compiler=gcc compiler.version=13 …`). Enables `conan install` without manual profile authoring.
- **`tool build docker`** _(medium)_ — `tool build docker --preset gcc-release-static-x86_64 [--image ubuntu:24.04]` builds the project inside a container for hermetic, reproducible artifacts. Dockerfile auto-generated from `tool.toml` build dependencies detected by `tool setup`.
- **Package Publishing** _(long-term)_ — `tool release publish [--to github|conan|vcpkg]` automates packaging and upload. GitHub Releases via `gh` CLI; Conan Center Index PR generation; vcpkg overlay port scaffolding.

#### Tooling Quality

- **Cross-Compile Sysroot Management** _(medium)_ — `tool sol sysroot add <arch> [--url <img>]` downloads/unpacks a sysroot tarball, registers it in `tool.toml [sysroots]`, and patches the toolchain cmake file. Simplifies AArch64 / RISC-V cross builds without a manual `CMAKE_SYSROOT` path.
- **LibFuzzer Native Integration** _(medium)_ — `cmake/Fuzzing.cmake` already has AFL++. Extend with libFuzzer: `-fsanitize=fuzzer-no-link` + per-target `enable_libfuzzer()`. CI nightly job runs both AFL++ and libFuzzer corpora, merges coverage, and uploads findings.
- **AMD HIP Support** _(deferred — requires HIP SDK, not installed on this system)_ — `cmake/HIP.cmake` mirroring `cmake/CUDA.cmake` structure. Implement when HIP SDK is available.

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

- **Lock Files:** ✅ DONE — `tool deps lock [--managers vcpkg|conan|pip] [--dry-run]` generates `vcpkg.lock.json` (manifest-hash + resolved entries), `conan.lock` (`conan lock create` or snapshot), and `requirements-dev.lock.txt` (`pip-compile` or `pip freeze`). `tool deps verify` checks staleness. `tool deps list` lists all manifests.

## Git leak detection (gitleaks) — ✅ DONE

- **Pre-Commit Hook:** ✅ DONE — `.pre-commit-config.yaml` with gitleaks v8.18.4 hook (blocks commits with secrets), plus pre-commit-hooks, ruff, cmake-format, clang-format.
- **CI Integration:** ✅ DONE — `.github/workflows/gitleaks.yml` scans all push/PR events + weekly schedule. SARIF upload on failure. PR commenting via `GITLEAKS_ENABLE_COMMENTS`.
- **Custom Rules:** ✅ DONE — `.gitleaks.toml` with 3 custom rules (CMake private key, SSH credentials, API Bearer tokens) and project-specific allowlists.
- **Reporting & Alerts:** ✅ DONE — SARIF reports uploaded to GitHub Security; CI workflow fails on detected secrets.

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
