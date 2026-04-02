# dummy_lib

**Version:** 2.5.0 (independent of the solution version)

Example library demonstrating per-library versioning, export headers, and
compile-time build metadata via `BuildInfo.h`.

## Usage

```cpp
#include <dummy_lib/dummy_lib.h>
#include "BuildInfo.h"      // dummy_lib_info::project_version == "2.5.0"
#include "ProjectInfo.h"    // convenience single-include

auto msg = dummy_lib::get_greeting();

// Access this library's own build metadata
std::cout << dummy_lib_info::project_name    << "\n";
std::cout << dummy_lib_info::project_version << "\n";  // "2.5.0"
std::cout << dummy_lib_info::compiler_id     << "\n";

// Print everything at once
BUILD_INFO_PRINT_ALL(std::cout, dummy_lib_info);
```

## Per-library version

Each library declares its own version in its `CMakeLists.txt`:

```cmake
target_generate_build_info(dummy_lib
    NAMESPACE dummy_lib_info
    PROJECT_VERSION "2.5.0"   # ← independent from the solution version
)
```

This version is embedded at compile time into `dummy_lib_info::project_version`
and is distinct from the top-level solution version (`main_app_info::project_version`).

## Build options

| CMake variable | Default | Effect |
|---|---|---|
| `DUMMY_LIB_CXX_STANDARD` | `""` | Per-lib C++ standard override (14/17/20/23) |
