# Build Settings Reference

All options are passed as `-D<OPTION>=ON/OFF` to CMake or set via a preset.

## Core Build

| Option | Default | Description |
|---|---|---|
| `BUILD_SHARED_LIBS` | `OFF` | `OFF` = Static (`.a`/`.lib`), `ON` = Shared (`.so`/`.dll`) |
| `CMAKE_BUILD_TYPE` | preset | `Debug` / `Release` / `RelWithDebInfo` |
| `CMAKE_CXX_STANDARD` | *auto* | Auto-detected; highest standard the compiler supports (up to C++23). Override: `-DCMAKE_CXX_STANDARD=20` |
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

### C++ Standard Auto-Detection

`cmake/CxxStandard.cmake` is included early in `CMakeLists.txt` and probes
`CMAKE_CXX_COMPILE_FEATURES` to identify the highest C++ standard the active
compiler supports (C++23 → C++20 → C++17 → C++14 → C++11).  The result is
stored in the CMake cache as `CMAKE_CXX_STANDARD` only if the user has **not**
already set it (explicit `-D` flag or preset `cacheVariable` always wins).

```
# What was auto-detected (non-interactive):
cmake --preset gcc-debug-static-x86_64 -N  # -N = no build, just configure
# Look for the line:
# [CxxStd] Auto-detected C++ standard: C++20
```

| Situation | Behaviour |
|---|---|
| User passes `-DCMAKE_CXX_STANDARD=17` | Respected; auto-detect skipped |
| Preset sets `cacheVariables.CMAKE_CXX_STANDARD` | Respected |
| Neither set | Highest supported std (GCC 13 → C++23, Clang 14 → C++20, …) |

### CUDA Device-Code C++ Standard

When `ENABLE_CUDA=ON`, `cmake/CUDA.cmake` calls `cuda_compatible_cxx_standard()`
(from `CxxStandard.cmake`) to map the toolkit version to the maximum C++
standard usable in **device code** (`.cu` files).  Host `.cpp` files always
use the host `CMAKE_CXX_STANDARD` and are unaffected.

| CUDA Toolkit | Max device-code C++ standard |
|---|---|
| < 9.0 | C++11 |
| 9.0 – 10.x | C++14 |
| 11.0 – 12.1 | C++17 |
| ≥ 12.2 | C++20 |

A CMake warning is emitted if the host standard exceeds the device-code limit:

```
[CUDA] Host C++ standard (C++20) exceeds CUDA 12.0 device-code limit (C++17).
  • .cu device code will be compiled with C++17.
  • Host .cpp files are unaffected (still C++20).
```

Override the device-code standard explicitly:

```bash
cmake --preset gcc-release-static-x86_64 -DENABLE_CUDA=ON \
  -DCMAKE_CUDA_STANDARD=17   # pin device std
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
| `ENABLE_CUDA` | `OFF` | CUDA GPU compute support (requires CUDA toolkit) |
| `CMAKE_CUDA_ARCHITECTURES` | `native` | GPU arch: `native` \| `all-major` \| `75;86;89` |
| `CMAKE_CUDA_STANDARD` | *auto* | Device-code C++ std (derived from CUDA toolkit version) |
| `CUDA_COMPILER` | `nvcc` | `clang` = use clang as CUDA compiler (requires clang ≥ 14) |
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
