# CppCmakeProjectTemplate — Capabilities Reference

This document lists all completed and production-ready features.

---

## Unified CLI & Tooling Framework

- **Unified CLI (`tool.py`):** Single entrypoint for all commands (`build`, `lib`, `sol`) and dynamic plugins (`plugins/`).
- **Modern Directory Layout:** Clear separation — `core/utils` (infra), `core/commands` (logic), `plugins/` (extensions).
- **Structured Logging:** Standard log levels, persistent log storage.
- **Standardized Results:** Commands return `CLIResult` with `--json` for automation.
- **Shared Session Persistence:** `load_session()` / `save_session()` / `backup_session()` via `[session]` in `tool.toml`.
- **Verification Harness:** `scripts/plugins/verify.py` automates build/test/extension flows.
- **Python Environment Automation:** `scripts/plugins/setup.py --env` creates cross-platform venvs.
- **Extension Packaging:** Reliable `.vsix` production under `extension/`.
- **Library Packaging Helpers:** `core.libpkg` modular helper surface.

## Project Creation & Generation

- **Interactive Wizard (`tool new`):** Prompts for name, author, license, C++ standard, profile, libs, apps, feature toggles. `--non-interactive` uses git config defaults. Generates into subdirectory with auto `git init`.
- **In-Place Adoption (`tool adopt`):** Like `cargo init` — auto-detects existing C++ sources, identifies libraries and apps (via `main()` heuristic), generates `tool.toml` + CMake scaffolding around them. Supports `--non-interactive` for CI and `--force` to overwrite.
- **Generation Profiles:** 5 profiles (`full`, `minimal`, `library`, `app`, `embedded`) control which components are generated.
- **Feature Toggles:** `--with`/`--without` flags for granular control. `--explain` previews effective settings.
- **License Engine (`tool license`):** `recommend` (decision tree), `list` (7 licenses), `--apply` writes to `tool.toml`.
- **Generator Debug & Observability:** `--debug` (tracebacks + per-component timing), `--verbose` (progress messages), `--json` (machine-readable output).
- **Generated File Cleanup:** When a component is disabled (e.g. `--without ci`), previously generated files tracked in the manifest are automatically removed. User-modified files are preserved with a warning.
- **CMakePresets Generator Component:** `presets` registered in the generator engine — `tool generate` also regenerates `CMakePresets.json` from `tool.toml [presets]`.
- **Config Validation (`tool validate`):** Schema-based validation for `tool.toml` — reports unknown sections/keys, type mismatches, invalid enum values, duplicate lib/app names, broken app→lib dependencies, and Levenshtein-based "did you mean?" typo suggestions.
- **DevContainer Generation:** `.devcontainer/devcontainer.json` auto-generated with Ubuntu 24.04, CMake + Python features, C++ VS Code extensions, and `postCreateCommand` running `tool setup --install`. Gated by `devcontainer` feature flag (enabled in `full` profile).

## Build System

- **Modern CMake (3.25+):** Target-based structure, no global flags.
- **Preset Matrix:** 34 ready presets — Linux, Windows, macOS, Embedded (ARM).
- **CMakePresets.json Generator:** `tool presets generate` reads `tool.toml [presets]`, generates full preset matrix with per-dimension filters, constraint matrix, auto-backup, `--dry-run`.
- **`tool presets list` / `validate`:** List visible presets, validate via `cmake --list-presets`.
- **MSVC Consistency:** Automatic `/MT` or `/MD` selection.
- **Per-Target BuildInfo:** Per-target versioning and git metadata.
- **Dynamic Feature Flags:** Build-time feature toggles.
- **Build Configuration Summary:** `build/build_config.json` emitted at build time.

## Static Builds & Cross-Compilation

- **musl libc / Fully Static Builds:** `cmake/toolchains/x86_64-linux-musl.cmake` — zero-dependency static binaries. Auto-detects musl-cross-make or `musl-gcc`. Alpine Docker support. Sanitizers disabled (incompatible). Optional `-static-pie` via `MUSL_STATIC_PIE=ON`.
- **Zig cc + musl:** `cmake/toolchains/x86_64-linux-musl-zig.cmake` — Zig ships with musl built-in. Creates wrapper scripts.
- **aarch64-linux-musl:** ARM64 fully static builds. `aarch64-linux-musl-zig` for zero-install cross-compilation.
- **Cross-Compilation:** 3 toolchains + 5 presets (embedded/aarch64). MSVC ARM64 support. Platform-aware skip rules.
- **vcpkg musl triplets:** `triplets/` overlay with 4 custom triplets.
- **Conan musl profiles:** Automatic arch mapping, hard skip rules, toolchain injection.
- **Docker Consolidation:** `docker/Dockerfile` (Ubuntu), `Dockerfile.alpine` (musl), `Dockerfile.zig-musl` (Zig).

## Distribution & Template Engine

- **Jinja2 Migration:** Integrated for `libpkg` and `sol` with fallback.
- **Bootstrap (`tool setup`):** Checks dependencies, `--install` via apt/brew/dnf/pacman. Creates/populates Python venv.
- **Rollback & Recovery:** `Transaction` helper for atomic file operations.

## Test Strategy & CI

- **Transactional Library Management:** `rename`, `move`, `remove` with CMake reference updates. `--dry-run`, `--yes`, `Transaction` rollback.
- **Dependency Awareness:** `tool lib tree` and `tool lib info` parse actual CMake dependencies.
- **Project Health:** `tool lib doctor` detects orphaned entries and broken structures.
- **Deterministic CI:** Optimized with caching, conditional builds, cross-platform verification.
- **App Scaffolding:** `tool sol target add` for automated app creation.

## Safety, Hardening & Sanitizers

- **Security Profiles:** `normal` → `strict` → `hardened` → `extreme` (Rust-like).
- **Sanitizer Selection:** `tool build --sanitizers asan ubsan` or `--sanitizers all`.
- **Per-Target Overrides:** `-D<TARGET>_ENABLE_HARDENING=ON/OFF`, `-D<TARGET>_ENABLE_ASAN=ON/OFF`.
- **Dynamic `.clang-tidy`:** Generated based on active profile via Jinja2.
- **Security Audit:** `tool security scan` — OSV-Scanner + Cppcheck, tiered policy.
- **CVE Scanning:** `osv-scanner` for dependency vulnerabilities.
- **Fuzz Testing:** libFuzzer harness, AFL++ CI (nightly), seed-corpus management, crash triage.
- **Static Analysis:** `clang-tidy --fix` automation and CI job.
- **Security Hardening:** `cmake/Hardening.cmake` — stack canaries, PIE, RELRO, CFI, FORTIFY_SOURCE, MSVC equivalents.
- **Cppcheck Acceleration:** `--cppcheck-jobs N` (parallel), `--cppcheck-checks full|minimal`, `--cppcheck-paths`, `--fast`. CI tiering + caching.
- **Reusable CI Workflow:** `.github/workflows/reusable-ci.yml`.

## Performance & Optimization

- **Performance Tracking:** `tool perf track` — size + build-time baseline in `build_logs/perf_baseline.json`.
- **Performance Budget:** `tool perf check-budget` — compare vs baseline, fail on regressions.
- **PGO:** `cmake/PGO.cmake` — two-phase PGO (GCC, Clang, MSVC) + BOLT post-link.
- **LTO:** `cmake/LTO.cmake` — CheckIPOSupported, thin LTO for Clang.
- **Build Caching:** `cmake/BuildCache.cmake` — auto-detects ccache/sccache.
- **Build Visualization:** `tool perf graph` — dependency graph via `cmake --graphviz`.
- **Embedded Targets:** `cmake/EmbeddedUtils.cmake` — binary outputs, map files, memory usage, linker scripts.
- **Code Size Analysis:** `tool perf size` — binary analysis with JSON report.
- **Build Time Analysis:** `tool perf build-time` — Ninja `.ninja_log` analysis.
- **Compiler Explorer:** `tool perf godbolt` — Godbolt API, `--save`, `--json`.
- **Performance Profiling:** `tool perf stat` — wraps `perf stat` / `time -v`. `tool perf record` for flame graphs.
- **Perf Regression CI:** `.github/workflows/perf_regression.yml` — 10% size / 25% time thresholds.
- **Runtime Metrics:** `perf::ScopedTimer` and `perf::ThroughputCounter` — header-inline.
- **Memory Analysis:** `tool perf valgrind [--vg-tool memcheck|massif]`.
- **Concurrency Analysis:** `tool perf concurrency` — helgrind/DRD. TSan via `--sanitizers tsan`.
- **Vectorization:** `tool perf vec` — compiler vectorization remarks. `-DENABLE_VEC_REPORT=ON`.
- **Auto-Parallelization:** `cmake/OpenMP.cmake` — `enable_openmp()`, `enable_openmp_simd()`, `enable_auto_parallelization()`.
- **Zero-Cost Abstractions:** `[[likely]]`/`[[unlikely]]`, `ATTR_HOT`/`ATTR_COLD`/`ATTR_PURE`/`ATTR_NOINLINE`.
- **Size Delta Tracking:** `tool perf size-diff` — `.text`/`.data`/`.bss` vs baseline.
- **Auto-Tuner:** `tool perf autotune` — hill/grid/random/anneal strategies.
- **Auto-Tuner V2:** `tool perf promote` (preset promotion), `tool perf hw-recommend` (CPU-aware flags), `--repeat N` (noise reduction).

## Allocators

- **Allocator Backends:** `cmake/Allocators.cmake` — mimalloc, jemalloc, tcmalloc. `tool build --allocator {default|mimalloc|jemalloc|tcmalloc}`.
- **Per-Target & Global Override:** `ENABLE_ALLOCATOR_OVERRIDE_ALL`. Zero code changes required.
- **Dependency Integration:** Conan `allocator` option, vcpkg features, FetchContent fallback (mimalloc).
- **Preset Variants:** `tool.toml [presets] allocators` dimension. `tool presets generate --allocator mimalloc,jemalloc`.
- **Pool APIs:** `cmake/PoolAllocator.h` — `StackPool<N>`, `UnsyncPool`, `SyncPool`. C++17, header-only.

## GPU & Compute

- **Qt5/Qt6:** `cmake/Qt.cmake` — auto-detect, `target_link_qt()`, AUTOMOC/AUTOUIC/AUTORCC.
- **CUDA:** `cmake/CUDA.cmake` — WSL-aware, `enable_cuda_support()`, `target_add_cuda()`. Clang-as-CUDA fallback.
- **AMD HIP:** `cmake/HIP.cmake` — `enable_hip_support()`, `target_add_hip()`. Auto-detect GPU.
- **Intel SYCL/DPC++:** `cmake/SYCL.cmake` — `enable_sycl_support()`, `target_add_sycl()`.
- **Apple Metal:** `cmake/Metal.cmake` — `enable_metal_support()`, `target_add_metal()`, shader compilation pipeline.
- **CUDA-Aware C++ Standard:** `cuda_compatible_cxx_standard()`.
- **Auto-Detect C++ Standard:** `cmake/CxxStandard.cmake` — three-strategy pipeline.

## C++ Modernity & DX

- **C++20 Modules:** `cmake/CxxModules.cmake` — `enable_cxx_modules()`, CMake 3.28+. `tool lib add --modules`.
- **IWYU:** `cmake/IWYU.cmake` + `tool format iwyu [--target <lib>] [--fix]`.
- **Binary Reproducibility:** `cmake/Reproducibility.cmake` — `SOURCE_DATE_EPOCH`, `ar -D`, file-prefix-map.

## Ecosystem & Integration

- **Conan 2.0 Profiles:** `tool deps conan-profile generate`.
- **Docker Build:** `tool build docker`.
- **Package Publishing:** `tool release publish --to github|conan|vcpkg`.
- **Sysroot Management:** `tool sol sysroot add <arch>`.
- **LibFuzzer Integration:** `cmake/Fuzzing.cmake`.
- **Lock Files:** `tool deps lock`, `tool deps verify`.

## Versioning & Release

- **Single-Source VERSION:** Root `VERSION` file (`<major>.<middle>.<minor>+<revision>`).
- **Release CLI:** `tool release bump|set|set-revision|tag|publish|unpublish`.
- **CMake Integration:** `project(... VERSION ...)` reads from `VERSION`.
- **CI Release:** `.github/workflows/release.yml` with `run_number` revision.

## Security Extras

- **Git Leak Detection:** `.pre-commit-config.yaml` (gitleaks v8.18.4), `.github/workflows/gitleaks.yml`, `.gitleaks.toml`.

## Configuration

- **Shell Completion (`tool completion`):** Generates Bash, Zsh, and Fish completion scripts for all CLI commands, subcommands, and global flags. `tool completion bash|zsh|fish` outputs the script; `--install` auto-installs for the current shell.
- **`tool.toml`:** 9+ sections. Read by `config_loader.py` via `tomllib`/`tomli`. CLI args override.
- **Session State:** `[session]` section. `tool session save/load/set`.

## UI

- **TUI:** `tool tui` dispatches to `scripts/tui.py`.
- **Live Doc Server:** `tool doc serve [--port N] [--open]`. `tool doc build` (mkdocs/sphinx).

## Granular Control

All per-script and per-target toggles as `-D` CMake options and CLI flags:

- **Build**: `--profile`, `--sanitizers`, `--preset`, `-D<TARGET>_ENABLE_*`
- **Fuzzing**: `-DENABLE_FUZZING`, `-DENABLE_AFL`, `--timeout-ms`, `--target`/`--corpus-root`
- **Security Scan**: `--install`, `--format`, `--fail-on-severity`, `--suppressions`
- **clang-tidy / format**: `format tidy-fix`, `--dry-run`, `--apply`, `--checks`
- **CI / Automation**: `--skip-ci`, `--ci-mode`, `--report-artifact`, `--retain-days`
- **Release & Packaging**: `--install`, `--dry-run`, `--signing-key`, `--publish`

## Internal Tooling Refactor _(Completed)_

SOLID-based restructuring of `scripts/` (~10,500 lines across 53 files).

| Phase | Scope | Status |
| ----- | ----- | ------ |
| Faz 0: Foundation | cmake_parser, command_utils, Jinja centralization | ✅ |
| Faz 1: perf.py | ~1840 lines → 8 modules in `commands/perf/` | ✅ |
| Faz 2: sol.py | ~1260 lines → 7 modules in `commands/sol/` | ✅ |
| Faz 3: build.py | ~674 lines → 4 modules in `commands/build/` | ✅ |
| Faz 5: lib.py | ~545 lines → 4 modules in `commands/lib/` | ✅ |
| Faz 7: E2E Tests | 75/75 tests passing | ✅ |
| Faz 8: References | AGENTS.md updated | ✅ |

## Full Generative Refactor _(Completed)_

`tool.toml` is the single declarative source (Cargo.toml model). Everything outside `scripts/` is generated by Python scripts. A project can be created from scratch in any empty directory via `tool generate --target-dir /path/to/project`.

**Principles:** Minimal code (only what's needed), user control (`--dry-run`, `--diff`, `--merge`, `--force`), hash-based tracking (`.tool/generation_manifest.json`), selective generation (`--component <X>`).

| Phase | Scope | Status |
| ----- | ----- | ------ |
| Faz 0: Foundation | Generator engine, manifest, merge, tool.toml schema, config_loader | ✅ |
| Faz 1: Root CMake | Root CMakeLists.txt + subdirectory aggregators | ✅ |
| Faz 2: Apps + Libs | App/lib scaffolding (CMakeLists, main.cpp, headers) | ✅ |
| Faz 3: cmake/ Modules | 22 STATIC + 2 DYNAMIC + 2 PARAMETRIC cmake modules, headers, toolchains | ✅ |
| Faz 4: CI/CD | GitHub workflows, actions, issue templates | ✅ |
| Faz 5: Deps + Hooks | vcpkg.json, conanfile.py, pre-commit, gitleaks config | ✅ |
| Faz 6: Docker/Docs/Configs | Dockerfiles, docs/, .vscode/, .gitignore, .clang-*, extension/ | ✅ |
| Faz 7: Unified Command | `tool generate` CLI (--target-dir, --component, --merge) | ✅ |
| Faz 8: Sources & Zero Diff | All 10 components (ci, cmake-dynamic, cmake-root, cmake-static, cmake-targets, configs, deps, docs, presets, sources) generate with **zero diff** against the actual project | ✅ |

### Generator Component Coverage (10/10 Zero Diff)

Every file outside `scripts/` is now fully reproducible from `tool.toml`:

- **sources:** C++ headers, sources, unit tests, benchmarks, fuzz harnesses, app mains, READMEs, VERSION — with 4 library templates (`exported`, `fuzzable`, `hasher`, `default`) and 4 app patterns (`main_app`, `demo_app`, `extreme_app`, `gui_app`)
- **cmake-root / cmake-targets:** Root CMakeLists.txt, per-lib/app/test CMakeLists.txt
- **cmake-static / cmake-dynamic:** 22 static + 2 dynamic cmake modules, toolchains, headers
- **ci:** GitHub Actions workflows, issue templates
- **deps:** vcpkg.json, conanfile.py
- **configs:** .vscode/, .gitignore, .clang-format, .clang-tidy, devcontainer.json, pre-commit
- **docs:** mkdocs.yml, docs/ pages, root README.md
- **presets:** CMakePresets.json with full preset matrix

**C++ Template Libraries:** Template-specific C++ code generation — `exported` (get_greeting, export macro, BuildInfo, 544-line compute benchmark), `fuzzable` (process_input → Result, fuzz harness), `hasher` (process_input → uint64_t fingerprinting). New projects get domain-relevant stubs rather than generic boilerplate.

**Benchmark Generation:** Full benchmark scaffolding generated from `tool.toml` — Sieve, Monte Carlo π, Matrix multiply (naive+tiled), Newton-Raphson √, Fibonacci, Sudoku solver, Mandelbrot, 1D/2D Convolution, library greeting baseline.
| Faz 8: Migration + E2E | 17 E2E tests (fresh gen, idempotency, conflict, manifest) | ✅ |
| Faz 9: Smoke Test | 14 smoke tests (minimal, full, header-only, profiles, etc.) | ✅ |

**cmake Module Classification:**

| Class | Strategy | Count |
| ----- | -------- | ----- |
| STATIC | Python string constants — embedded verbatim | 22 |
| DYNAMIC | Python f-string — receives tool.toml context | 2 (ProjectConfigs, FeatureFlags) |
| PARAMETRIC | Static skeleton + parameter injection | 2 (Allocators, StaticAnalyzers) |

**Generator Module Structure:** `scripts/core/generator/` — engine.py (orchestrator), wizard.py (interactive creation), manifest.py (hash tracking), merge.py (conflict resolution), cmake_dynamic.py, cmake_static/, cmake_root.py, cmake_targets.py, sources.py, ci.py, deps.py, configs.py, 31 tests.

## Generator Debug & Observability _(Completed)_

- **`--debug` flag:** Per-component timing (`⏱ component: 0.0123s`) + full tracebacks on generator/write failures.
- **`--verbose` flag:** Progress logging (`→ generating component: cmake-root`).
- **`--json` flag:** Machine-readable JSON output with created/written/skipped/conflicts/errors/timings.
- **Timing infrastructure:** `GenerateResult.timings` dict with per-component durations via `time.monotonic()`.
- **merge.py fix:** Silent exception in `_show_diff()` now logged via `Logger.warn()`.

## Documentation & Agent Unification _(Completed)_

- **GEMINI.md removed:** Content unified into `AGENTS.md` (single source of truth for AI agents).
- **AGENTS.md enhanced:** Added Repository Structure tree, updated documentation index references.
- **Pytest config fixed:** Added `pythonpath = ["scripts"]` and `scripts/core/generator/tests` to `testpaths` in `pyproject.toml`. All 31 generator tests pass in <2s.

## Documentation Generation _(Completed)_

- **Docs generator component** (`scripts/core/generator/docs.py`): Full documentation scaffolding as part of `tool generate`.
- **Configurable doc engine** (`tool.toml [doc].engine`): Supports `doxygen`, `mkdocs`, `sphinx`, or any combination.
- **Doxygen support:** Generates `Doxyfile` with project metadata, source paths, DOT graphs, extraction settings.
- **MkDocs support:** Generates `mkdocs.yml` with Material theme, navigation, Markdown extensions, search plugin.
- **Sphinx support:** Generates `docs/conf.py` + `docs/index.rst` with optional Breathe integration for Doxygen XML.
- **Markdown doc skeleton:** Always generates `docs/index.md`, `getting-started.md`, `api-reference.md`, `contributing.md` with project-aware content.
- **Profile-aware:** Disabled by default for `minimal` and `embedded` profiles; override with `--with docs`.
- **API docs toggle:** `doc.generate_api_docs = false` skips engine configs while still producing markdown skeleton.
- **Unified roadmap:** `docs/PLANS.md` and `docs/IDEAS.md` merged into single `docs/ROADMAP.md`.

## Enhanced Clean & Extension Refactor _(Completed)_

- **Comprehensive `build clean --all`:** Removes all build/generated artifacts — `build/`, `build-extreme/`, `build_logs/`, `dist/`, `*.egg-info`, `__pycache__` (recursive), `.mypy_cache/`, `.pytest_cache/`, `.ruff_cache/`, `.tool/`, `extension/templates/`, `extension/node_modules/`, `*.vsix`, `conan.lock`. Summary logging of what was removed.
- **Extension refactor:** VS Code extension `init` command now uses `cppcmake-tool new` CLI instead of copying template files. Removed `_sync_templates()`, `copyDir()`, and all template-copy infrastructure. Extension uses the same Python CLI that the terminal uses.
- **`.gitignore` gaps fixed:** Added missing entries: `build-extreme/`, `dist/`, `*.egg-info/`, `.tool/`, `conan.lock`.

## Generator Improvements — Phase 9 _(Completed)_

### Incremental Generation

- **Component-level input hashing:** Each generator component's inputs (full config + module source code) are hashed and stored in the manifest.
- **Automatic skip:** When `incremental=True` (or `generate.incremental = true` in tool.toml), components whose inputs haven't changed since the last run are skipped entirely.
- **Deterministic hashing:** Uses SHA-256 of canonical JSON config + generator source code for reliable change detection.
- **5 dedicated tests** validating skip behavior, config-change detection, manifest persistence, and config-flag activation.

### Minimal Seed Mode Proof

- **End-to-end proof:** A minimal `tool.toml` config can bootstrap a complete, self-consistent project with libraries, apps, tests, and CMake presets.
- **Dependency wiring verified:** Generated CMakeLists.txt files correctly reflect inter-library and app-to-lib dependencies.
- **Idempotent + incremental:** Seed mode projects can be regenerated idempotently, and incremental mode skips all components when unchanged.
- **Profile-aware:** Minimal profile generates fewer files than full profile.
- **5 dedicated E2E tests** covering complete project structure, dependency wiring, idempotency, incremental skip, and profile comparison.

### Cross-Reference Validation (`tool validate`)

- **Lib-to-lib dependency validation:** `_cross_validate()` now checks that library deps reference declared libraries (previously only app deps were checked).
- **Template name validation:** Validates `template` field against known set: `{default, exported, fuzzable, hasher, normal}`.
- **Circular dependency detection:** New `_detect_circular_deps()` function using DFS graph coloring (WHITE/GRAY/BLACK) with cycle path reporting.

### Edge Case Test Suite

- **27 new edge case tests** in `test_generator_edge_cases.py` covering: corrupted/missing/wrong-version manifest recovery, hash consistency, file modification detection, invalid/valid template names, undeclared lib deps, circular deps (self-loop, 2-lib, 3-lib), valid DAGs, app dep validation, duplicate lib names, benchmarks without fuzz, underscore names, interface libraries, with+without same feature, invalid profiles, scale test (20 libraries), chained dependency wiring, SKIP/OVERWRITE conflict policies, partial conflicts.

### Quick Fixes

- **Parameterized preset:** `sources.py` now uses `ctx.presets.get("default_preset", ...)` instead of hardcoded `gcc-debug-static-x86_64`.
- **Specific exception types:** Replaced 5 bare `except Exception` with targeted types across `release.py`, `deps.py`, `security.py`.
- **CI observability:** `ci.py` now logs a warning when `.github/workflows/` directory is not found.

## Cross-Platform & ROADMAP Phase _(Completed)_

### Cross-Platform Support

- **macOS / AppleClang presets:** `macos-base` and `macos-appleclang-base` hidden presets. AppleClang compiler support restricted to x86_64/arm64/aarch64.
- **MSVC presets:** Full MSVC compiler support with Windows-native arch mapping and `/MT`/`/MD` selection.
- **Multi-platform code coverage:** `CodeCoverage.cmake` now supports MSVC (OpenCppCoverage), LLVM (llvm-profdata + llvm-cov), and GCC (lcov + genhtml).
- **Cross-platform profiling:** macOS: `leaks` for memory analysis, `gtime` or `/usr/bin/time -l` for CPU stats, `xcrun xctrace` hints. Windows: VS Diagnostic Tools / WPA guidance.
- **Setup plugin:** `winget` and `choco` package manager detection on Windows with full install-command mapping.

### AI Agent Integration

- **AGENTS.md generator component:** New `agents` component in COMPONENT_REGISTRY generates `AGENTS.md`, `.github/copilot-instructions.md`, `.cursorrules`, and `.clinerules` from `tool.toml` metadata.
- **Profile-aware:** Included in all 5 profiles (full, minimal, library, app, embedded).

### Build Automation

- **Watch Mode (`tool build watch`):** Polling-based auto-rebuild on source changes in `libs/`, `apps/`, `cmake/`. Configurable interval, detects modified/deleted files.
- **Error Diagnostics (`tool build diagnose`):** Parses compiler/CMake error output and provides human-friendly suggestions (Rust-style). Supports stdin or log file input.
- **Error Diagnostics CLI (`tool diagnostics`):** Standalone command with `--log`, `--check` for quick build + diagnose.

### Dependency Management

- **SBOM Generation (`tool sbom`):** Software Bill of Materials in SPDX 2.3 and CycloneDX 1.5 JSON formats. Auto-detects dependencies from vcpkg.json, conanfile.py, requirements-dev.txt.
- **Dependency Update Check (`tool deps update`):** Checks for newer pip packages, lists vcpkg/Conan version pins with upgrade tips. Per-manager filtering via `--managers`.

### WebAssembly

- **Emscripten toolchain:** `cmake/toolchains/wasm32-emscripten.cmake` for WASM builds. Delegates to Emscripten's own CMake toolchain with project defaults. Skip rules for WASM arches in preset generator.

### Generator Architecture

- **Component Dependency Graph:** Components declare dependencies via `COMPONENT_DEPS` dict. Generation order is topologically sorted, with circular dependency detection.
- **Nix Flake Generation:** `flake.nix` generated via configs component when `nix` feature is enabled. Also available as standalone `tool nix generate`.

### Project Management

- **Migration Wizard (`tool migrate`):** Detects current project state via manifest, identifies drift, offers incremental upgrades with dry-run support.
- **Templates Gallery (`tool templates`):** Curated starter templates (minimal, library, networking, game-engine, embedded-firmware) selectable via `tool templates list` / `create`.
