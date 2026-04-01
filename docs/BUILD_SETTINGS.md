# Build Settings Reference

All options are passed as `-D<OPTION>=ON/OFF` to CMake or set via a preset.

## Core Build

| Option | Default | Description |
|---|---|---|
| `BUILD_SHARED_LIBS` | `OFF` | `OFF` = Static (`.a`/`.lib`), `ON` = Shared (`.so`/`.dll`) |
| `CMAKE_BUILD_TYPE` | preset | `Debug` / `Release` / `RelWithDebInfo` |
| `CMAKE_CXX_STANDARD` | `17` | `14` / `17` / `20` / `23` — solution-wide |
| `ENABLE_WERROR` | `OFF` | Treat warnings as errors |
| `ENABLE_UNITY_BUILD` | `OFF` | Unity builds for faster compilation |
| `ENABLE_DOCS` | `OFF` | Build Doxygen documentation |

Per-library C++ standard override (does not affect other targets):

```bash
cmake --preset gcc-debug-static-x86_64 -DDUMMY_LIB_CXX_STANDARD=20
# or via toolsolution (use unified CLI):
python3 scripts/tool.py sol upgrade-std --std 20 --target dummy_lib
# solution-wide:
python3 scripts/tool.py sol upgrade-std --std 20
```

## Tests

| Option | Default | Description |
|---|---|---|
| `ENABLE_UNIT_TESTS` | `ON` | Master switch — `OFF` removes all test dependencies |
| `ENABLE_GTEST` | `ON` | GoogleTest (auto-downloaded) |
| `ENABLE_CATCH2` | `OFF` | Catch2 v3 (auto-downloaded) |
| `ENABLE_BOOST_TEST` | `OFF` | Boost.Test (requires `ENABLE_BOOST=ON`) |
| QTest | auto | Enabled automatically when `ENABLE_QT=ON` |

## Sanitizers

| Option | Default | Description |
|---|---|---|
| `ENABLE_ASAN` | `OFF` | AddressSanitizer |
| `ENABLE_UBSAN` | `OFF` | UndefinedBehaviorSanitizer |
| `ENABLE_TSAN` | `OFF` | ThreadSanitizer (mutually exclusive with ASan/UBSan) |

## Static Analysis & Coverage

| Option | Default | Description |
|---|---|---|
| `ENABLE_CLANG_TIDY` | `OFF` | clang-tidy |
| `ENABLE_CPPCHECK` | `OFF` | cppcheck |
| `ENABLE_COVERAGE` | `OFF` | LCOV/GCOV HTML report |

```bash
cmake --preset gcc-debug-static-x86_64 -DENABLE_COVERAGE=ON
cmake --build --preset gcc-debug-static-x86_64 --target coverage_report
```

## Optional Frameworks

| Option | Default | Description |
|---|---|---|
| `ENABLE_QT` | `OFF` | Qt5 or Qt6 (auto-detected) |
| `ENABLE_QML` | `OFF` | Qt QML (requires `ENABLE_QT=ON`) |
| `ENABLE_BOOST` | `OFF` | Boost libraries |
| `BOOST_COMPONENTS` | `""` | Semicolon-separated: `filesystem;system` |

## Performance & Optimization

| Option | Default | Description |
|---|---|---|
| `ENABLE_LTO` | `OFF` | Link-Time Optimization (full LTO or Thin LTO for Clang) |
| `ENABLE_CCACHE` | `ON` | Auto-detect ccache/sccache as compiler launcher |
| `CACHE_PROGRAM` | *(auto)* | Override compiler cache program path |
| `PGO_MODE` | `""` | `generate` = instrument build; `use` = apply profile |
| `PGO_PROFILE_DIR` | `build/pgo-profiles` | Profile data directory for PGO |

### LTO usage

```bash
cmake --preset gcc-release-static-x86_64 -DENABLE_LTO=ON
# Per-target only:
cmake --preset gcc-release-static-x86_64 -DMAIN_APP_ENABLE_LTO=ON
# Thin LTO (Clang only, faster link):
python3 scripts/tool.py build build --lto
```

### PGO workflow (two-phase)

```bash
# Phase 1 — instrumented build
cmake --preset gcc-release-static-x86_64 -DPGO_MODE=generate
cmake --build --preset gcc-release-static-x86_64
./build/gcc-release-static-x86_64/apps/main_app/main_app  # exercise code

# Clang only: merge profile data
llvm-profdata merge -output=build/pgo-profiles/default.profdata build/pgo-profiles/*.profraw

# Phase 2 — optimized build
cmake --preset gcc-release-static-x86_64 -DPGO_MODE=use
cmake --build --preset gcc-release-static-x86_64
```

### Build cache (ccache/sccache)

Auto-enabled when `ccache` or `sccache` is on PATH. Disable with:

```bash
cmake --preset gcc-debug-static-x86_64 -DENABLE_CCACHE=OFF
```

### Analyze binary sizes & build times

```bash
python3 scripts/tool.py perf size
python3 scripts/tool.py perf build-time
# With explicit build dir:
python3 scripts/tool.py perf size --build-dir build/gcc-release-static-x86_64
```

## MSVC Runtime

| | Static build | Shared build |
|---|---|---|
| Release | `/MT` | `/MD` |
| Debug | `/MTd` | `/MDd` |

Set automatically from `BUILD_SHARED_LIBS`. Mixing runtimes causes `LNK2038`.
