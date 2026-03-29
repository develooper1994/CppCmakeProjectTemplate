# Compile-time Build Info & Feature Flags

Every target built with `target_generate_build_info` gets a `BuildInfo.h` at compile time.
Include `ProjectInfo.h` as a single-header convenience wrapper:

```cpp
#include "ProjectInfo.h"   // BuildInfo.h + FeatureFlags.h + BuildInfoHelper.h

// Print everything (build info + git + feature flags)
BUILD_INFO_PRINT_ALL(std::cout, main_app_info);

// Short version line: "CppCmakeProjectTemplate v1.0.5+0 (main@abc1234)"
//
// Version format: <major>.<middle>.<minor>+<revision>
// - The three-part base (major.middle.minor) is used by CMake `project(... VERSION ...)`.
// - The optional `+revision` is build metadata (CI run number, build counter).
std::string ver = BUILD_INFO_VERSION_LINE(main_app_info);

// Access individual fields
std::cout << main_app_info::project_version << "\n";  // "1.0.5"
std::cout << main_app_info::git_branch      << "\n";  // "main"
std::cout << main_app_info::compiler_id     << "\n";  // "GNU"

// Compile-time feature check
#if FEATURE_ASAN
    std::cout << "Running with AddressSanitizer\n";
#endif

// Runtime feature list
for (const auto& f : project_features::features)
    std::cout << (f.enabled ? "[x]" : "[ ]") << " " << f.name << "\n";
```

Each library has its **own independent version**:

```cpp
#include "BuildInfo.h"   // generated into dummy_lib's include path

// dummy_lib version — independent from the solution version
std::cout << dummy_lib_info::project_version;  // "2.5.0"
std::cout << main_app_info::project_version;   // "1.0.5"
```

| C++ Symbol | Source | Notes |
|---|---|---|
| `<ns>::project_name` | `CMakeLists.txt` | Target name |
| `<ns>::project_version` | `target_generate_build_info(...PROJECT_VERSION)` | Per-target |
| `<ns>::git_hash` | `git rev-parse HEAD` | At configure time |
| `<ns>::git_branch` | `git rev-parse --abbrev-ref HEAD` | At configure time |
| `<ns>::git_dirty` | `git diff --quiet` | `bool` |
| `<ns>::build_type` | `CMAKE_BUILD_TYPE` | Debug/Release/… |
| `<ns>::library_type` | CMake target type | Static/Shared/Executable |
| `<ns>::compiler_id` | `CMAKE_CXX_COMPILER_ID` | GNU/Clang/MSVC |
| `<ns>::build_timestamp` | configure time | UTC string |
| `FEATURE_GTEST` | `ENABLE_GTEST` | `0` or `1` |
| `FEATURE_ASAN` | `ENABLE_ASAN` | `0` or `1` |
| `PROJECT_SHARED_LIBS` | `BUILD_SHARED_LIBS` | `0` or `1` |
