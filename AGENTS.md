# AGENTS.md — AI Agent Execution Contract
# Read this file FIRST. It tells you what this repo is and how to work with it.

## What This Repository Is

A professional, multi-target C++ CMake project template and scaffold system.
It is **not** a single-purpose library — it is an **orchestrated project framework**
with full automation tooling. Do not re-invent things that already exist here.

## Existing Tooling (USE THESE, don't re-implement)

| Tool | Purpose |
|---|---|
| `python3 scripts/toollib.py add <n>` | Create new library skeleton |
| `python3 scripts/toollib.py remove/rename/move/deps/export/info/test` | Library management |
| `python3 scripts/toolsolution.py target/preset/toolchain/config/repo/test/upgrade-std` | Project orchestration |
| `python3 scripts/build.py build/check/clean/deploy/extension` | Build automation |
| `python3 scripts/install_deps.py` | Dependency management |
| `cmake --preset <name>` | Build with preset |
| `ctest --preset <name>` | Run tests |

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
5. **INTEGRATE** — Use `toollib.py` for new libs. Update CMake. Link deps. Add tests + README.
6. **VALIDATE** — `python3 scripts/build.py check --no-sync` must pass.
7. **OUTPUT** — Full, working result. No partial code.

## Forbidden Actions

- Editing `external/` directory
- Removing presets from `CMakePresets.json`
- Disabling `CMAKE_EXPORT_COMPILE_COMMANDS`
- Global CMake flags (always target-scoped)
- Large blind refactors across multiple subsystems
- Re-implementing what `toollib.py` or `toolsolution.py` already do

## File Structure

```
apps/          Executable targets (main_app, gui_app)
libs/          Library targets — each has CMakeLists.txt + README.md + include/ + src/ + docs/
tests/unit/    GoogleTest suites — one subdirectory per library
cmake/         Build system modules + generated headers
  BuildInfo.cmake        Per-target git/compiler metadata → BuildInfo.h
  FeatureFlags.cmake     All ENABLE_* options → FeatureFlags.h (dynamic, from PROJECT_ALL_OPTIONS)
  ProjectInfo.h          Single-include wrapper: BuildInfo + FeatureFlags + BuildInfoHelper
  BuildInfoHelper.h      BUILD_INFO_PRINT_ALL, BUILD_INFO_VERSION_LINE macros
  ProjectExport.cmake    find_package() support for libraries
  toolchains/            arm-none-eabi, linux-x86, template-custom-gnu
scripts/       Automation scripts (toollib.py, toolsolution.py, build.py, ...)
extension/     VS Code extension source and .vsix output
docs/          PLANS.md (pending features), EMBEDDED.md
external/      Third-party FetchContent deps (fetch_deps.cmake)
```

## Adding a New Library

```bash
# Normal library
python3 scripts/toollib.py add my_lib --deps core --link-app

# Header-only
python3 scripts/toollib.py add math_utils --header-only

# Interface (compile defs / include propagation only)
python3 scripts/toollib.py add feature_config --interface

# With external dep
python3 scripts/toollib.py deps my_lib --add-url https://github.com/fmtlib/fmt@10.2.1

# Add find_package() support
python3 scripts/toollib.py export my_lib
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

- After completing work: run `python3 scripts/build.py check --no-sync`
- Update `docs/PLANS.md`: mark completed tasks, add new discovered tasks
- Check `python3 scripts/toolsolution.py doctor` passes
- Check `python3 scripts/toollib.py doctor` passes
