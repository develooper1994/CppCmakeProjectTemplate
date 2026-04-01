# Performance & Optimization Guide

CMake modules, CLI tools, and C++ APIs for measuring and improving build and runtime performance.

---

## Build-time Caching (ccache / sccache)

Automatically detected when either tool is on `PATH`. Speeds up incremental and
CI builds by caching compiled object files.

| Priority | Tool | Notes |
|---|---|---|
| 1 | `sccache` | Distributed / S3 / Azure Blob backend support |
| 2 | `ccache` | Local disk cache |

```bash
# Check which cache is active (shown in configure output):
#   -- Build cache enabled: /usr/bin/ccache

# Disable:
cmake --preset gcc-debug-static-x86_64 -DENABLE_CCACHE=OFF

# Override with a specific binary:
cmake --preset gcc-debug-static-x86_64 -DCACHE_PROGRAM=/usr/local/bin/sccache
```

The active cache program is readable at runtime:

```cpp
#include "ProjectInfo.h"
std::cout << main_app_info::build_cache << "\n"; // "ccache" | "sccache" | "none"
```

---

## Link-Time Optimization (LTO)

LTO enables cross-translation-unit inlining and dead-code elimination at link
time, producing smaller and faster binaries at the cost of longer link times.

### CMake options

| Option | Scope | Effect |
|---|---|---|
| `-DENABLE_LTO=ON` | Global | Enable LTO for all targets that call `enable_lto_for_target()` |
| `-D<TARGET>_ENABLE_LTO=ON/OFF` | Per-target | Override global setting for one target |

```bash
# Release build with LTO:
cmake --preset gcc-release-static-x86_64 -DENABLE_LTO=ON
cmake --build --preset gcc-release-static-x86_64

# CLI shortcut:
python3 scripts/tool.py build build --lto
```

### Thin LTO (Clang only)

Thin LTO is ~10× faster than full LTO with similar benefits:

```cmake
# In your lib/app CMakeLists.txt:
enable_lto_for_target(my_target THIN)
```

### C++ query

```cpp
#include "ProjectInfo.h"
if constexpr (main_app_info::lto_enabled) {
    // LTO was active at build time
}
```

---

## Profile-Guided Optimization (PGO)

Two-phase process:

1. **Instrument** — build collects execution profiles.
2. **Optimize** — rebuild using the collected profile for data-driven optimization.

### Phase 1: Generate

```bash
cmake --preset gcc-release-static-x86_64 -DPGO_MODE=generate
cmake --build --preset gcc-release-static-x86_64

# Run the binary to collect profile data (exercise representative workloads):
./build/gcc-release-static-x86_64/apps/main_app/main_app
```

**Clang only** — merge raw profiles before Phase 2:

```bash
llvm-profdata merge \
  -output=build/pgo-profiles/default.profdata \
  build/pgo-profiles/*.profraw
```

### Phase 2: Use

```bash
cmake --preset gcc-release-static-x86_64 -DPGO_MODE=use \
      -DPGO_PROFILE_DIR=build/pgo-profiles
cmake --build --preset gcc-release-static-x86_64
```

### Per-target override

```cmake
enable_pgo_for_target(hot_lib)           # follows global PGO_MODE
set(HOT_LIB_ENABLE_PGO OFF CACHE BOOL "") # opt-out
```

### C++ query

```cpp
#include "ProjectInfo.h"
constexpr auto mode = main_app_info::pgo_mode; // "off" | "generate" | "use"
```

---

## Binary Size & Build Time Analysis

### Size report

```bash
python3 scripts/tool.py perf size
# Explicit preset dir:
python3 scripts/tool.py perf size --build-dir build/gcc-release-static-x86_64
```

Output: a formatted table of every `.a`, `.so`, and ELF executable, plus a
detailed JSON report at `build_logs/size_report.json`.

Bloaty (`bloaty`) is used automatically if installed for deep section analysis.

### Build time report

```bash
python3 scripts/tool.py perf build-time
# Force a timed rebuild with a specific preset:
python3 scripts/tool.py perf build-time --preset gcc-debug-static-x86_64
```

When a `.ninja_log` is present the top-20 slowest compilation units are shown
and a JSON report is written to `build_logs/build_time_report.json`.

---

## CMake Configure-Time Summary Table

Every `cmake` configure run prints a summary that includes the Performance
section:

```
┌──────────────────────────────────────────────────────┐
│  Build Configuration Summary
├──────────────────────────────────────────────────────┤
│  Project          CppCmakeProjectTemplate v1.0.6
│  ...
├──────────────────────────────────────────────────────┤
│  LTO              OFF                (-DENABLE_LTO)
│  PGO              OFF                (-DPGO_MODE)
│  Build cache      ccache             (-DENABLE_CCACHE)
├──────────────────────────────────────────────────────┤
```

---

## Recommended Optimization Profile for Release

```bash
cmake --preset gcc-release-static-x86_64 \
      -DENABLE_LTO=ON \
      -DENABLE_CCACHE=ON \
      -DPGO_MODE=use \
      -DPGO_PROFILE_DIR=build/pgo-profiles
cmake --build --preset gcc-release-static-x86_64 -j$(nproc)
```
