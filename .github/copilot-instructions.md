# GitHub Copilot Instructions

## Project Overview

This is a **professional C++ CMake project template** with full automation tooling.
Read `AGENTS.md` and `GEMINI.md` for the complete reference.

## Critical: Use Existing Tools

**Before writing any code or CMake, check if the tooling already handles it:**

```bash
python3 scripts/toollib.py --help       # Library management
python3 scripts/toolsolution.py --help  # Project orchestration
python3 scripts/build.py --help         # Build automation
```

## Adding a Library

```bash
python3 scripts/toollib.py add my_lib               # normal
python3 scripts/toollib.py add my_lib --header-only # header-only
python3 scripts/toollib.py add my_lib --interface   # interface target
python3 scripts/toollib.py add my_lib --template singleton  # pattern
python3 scripts/toollib.py deps my_lib --add-url https://github.com/fmtlib/fmt@10.2.1
python3 scripts/toollib.py export my_lib            # find_package support
```

## Validation (run after every change)

```bash
python3 scripts/build.py check --no-sync
```

## Mandatory Rules

- Every library needs: `CMakeLists.txt`, `README.md`, `include/<n>/`, `docs/`
- Normal libs also need: `src/<n>.cpp`, `tests/unit/<n>/`
- All CMake must be target-scoped — no global flags
- Never touch `external/` directly
- Never remove presets from `CMakePresets.json`
- C++ standard: use `target_generate_build_info` for per-lib versioning

## C++ Build Info

```cpp
#include "ProjectInfo.h"
BUILD_INFO_PRINT_ALL(std::cout, my_namespace);
#if FEATURE_ASAN
    // ASan enabled
#endif
```

## Code Conventions

- `PascalCase` for classes/structs, `lower_case` for functions/variables/namespaces
- `std::string_view` for const string parameters
- Smart pointers over raw pointers
- Arrange-Act-Assert for unit tests
