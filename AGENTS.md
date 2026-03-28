# AGENTS.md — AI Agent Execution Contract
# Read this file FIRST. It tells you what this repo is and how to work with it.

## What This Repository Is

A professional, multi-target C++ CMake project template and scaffold system.
It is **not** a single-purpose library — it is an **orchestrated project framework**
with full automation tooling. Do not re-invent things that already exist here.

## Existing Tooling (USE THESE, don't re-implement)

**Single entry point:** `python3 scripts/tool.py <command> [args]`

| Command | Purpose |
|---|---|
| `tool build check` | Configure + build + test + extension sync |
| `tool build build --preset <n>` | Configure + compile |
| `tool build clean [--all]` | Remove artifacts |
| `tool build extension [--install] [--publish]` | Build .vsix |
| `tool lib add <n> [--header-only\|--interface\|--template X]` | Create library |
| `tool lib remove/rename/move/deps/export/info/test` | Library management |
| `tool sol target/preset/toolchain/config/repo/test/upgrade-std/ci/doctor` | Orchestration |
| `tool sol --lib <toollib args>` | Library ops via sol |
| `tool tui` | Terminal UI |
| `tool setup [--install] [--all]` | Dependency management |
| `tool init --name MyProject` | Rename project |
| `tool hooks` | Install pre-commit hooks |
| `cmake --preset <n>` | Direct CMake build |
| `ctest --preset <n>` | Direct CTest run |

> **Internal modules** (`scripts/build.py`, `scripts/toollib.py`, `scripts/toolsolution.py`)
> are implementation details. Use `tool.py` for all automation.

### Available presets (naming: `<compiler>-<type>-<link>-<arch>`)
- Linux: `gcc-debug-static-x86_64`, `gcc-release-static-x86_64`, `clang-debug-static-x86_64`
- Windows: `msvc-debug-static-x64`, `msvc-release-static-x64`
- macOS: `clang-debug-static-x86_64`
- Embedded: `embedded-arm-none-eabi`

## Agent Workflow (MANDATORY — 7 Steps)

1. **ANALYZE** — Identify affected area: `libs/` `apps/` `tests/` `cmake/` `scripts/` `docs/`
2. **IMPACT** — New target? CMake change? Tests needed? Docs needed? Build impact?
3. **PLAN** — Choose minimal safe change. Avoid unrelated edits.
4. **IMPLEMENT** — Complete code only. No placeholders. Respect existing structure.
5. **INTEGRATE** — Use `tool lib add` for new libs. Update CMake. Link deps. Add tests + README.
6. **VALIDATE** — `python3 scripts/tool.py build check` must pass.
7. **OUTPUT** — Full, working result. No partial code.

## Forbidden Actions

- Editing `external/` directory
- Removing presets from `CMakePresets.json`
- Disabling `CMAKE_EXPORT_COMPILE_COMMANDS`
- Global CMake flags (always target-scoped)
- Large blind refactors across multiple subsystems
- Re-implementing what `tool lib` or `tool sol` already do
- Calling `toollib.py`, `toolsolution.py`, `build.py` directly (use `tool.py`)

## File Structure

```
apps/          Executable targets (main_app, gui_app)
libs/          Library targets — each has CMakeLists.txt + README.md + include/ + src/ + docs/
tests/unit/    GoogleTest suites — one subdirectory per library
cmake/         Build system modules + generated headers
  BuildInfo.cmake        Per-target git/compiler metadata → BuildInfo.h
  FeatureFlags.cmake     All ENABLE_* options → FeatureFlags.h (dynamic)
  ProjectInfo.h          Single-include wrapper: BuildInfo + FeatureFlags + BuildInfoHelper
  BuildInfoHelper.h      BUILD_INFO_PRINT_ALL, BUILD_INFO_VERSION_LINE macros
  ProjectExport.cmake    find_package() support for libraries
  toolchains/            arm-none-eabi, linux-x86, template-custom-gnu
scripts/
  tool.py                ← SINGLE ENTRY POINT
  core/commands/         build.py, lib.py, sol.py (façades over implementation modules)
  core/utils/common.py   Logger, CLIResult, GlobalConfig, run_proc
  plugins/               setup.py, init.py, hooks.py, hello.py
  build.py               Implementation (not for direct use)
  toollib.py             Implementation (not for direct use)
  toolsolution.py        Implementation (not for direct use)
  tui.py                 Terminal UI (also callable via: tool tui)
extension/     VS Code extension source and .vsix output
docs/          PLANS.md, EMBEDDED.md
external/      Third-party FetchContent deps (fetch_deps.cmake)
```

## Adding a New Library

```bash
# Normal library
python3 scripts/tool.py lib add my_lib --deps core --link-app

# Header-only
python3 scripts/tool.py lib add math_utils --header-only

# Interface (compile defs / include propagation only)
python3 scripts/tool.py lib add feature_config --interface

# Pattern-based scaffold
python3 scripts/tool.py lib add my_service --template singleton

# With external dep
python3 scripts/tool.py lib deps my_lib --add-url https://github.com/fmtlib/fmt@10.2.1

# Add find_package() support
python3 scripts/tool.py lib export my_lib
```

## Compile-time Build Info in C++

```cpp
#include "ProjectInfo.h"   // single include

BUILD_INFO_PRINT_ALL(std::cout, my_namespace);    // print all info
auto v = BUILD_INFO_VERSION_LINE(my_namespace);   // "Name v1.0 (main@abc1234)"
#if FEATURE_ASAN
    // ASan is enabled
#endif
for (const auto& f : project_features::features)
    std::cout << f.name << ": " << f.enabled << "\n";
```

## Per-library Independent Versioning

```cmake
target_generate_build_info(my_lib NAMESPACE my_lib_info PROJECT_VERSION "2.0.0")
```

## Priority Rules

1. Build integrity (never break the build)
2. Correctness
3. Isolation (no cross-contamination between targets)
4. Maintainability

## Agent Status Responsibility

- After completing work: run `python3 scripts/tool.py build check`
- Update `docs/PLANS.md`: mark completed tasks, add new discovered tasks
- Check `python3 scripts/tool.py sol doctor` passes
- Check `python3 scripts/tool.py lib doctor` passes
