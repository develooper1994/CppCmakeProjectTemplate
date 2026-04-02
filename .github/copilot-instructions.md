# GitHub Copilot Instructions

## Project Overview

This is a **professional C++ CMake project template** with full automation tooling.
Read `AGENTS.md` for the complete reference.

## Critical: Use Existing Tools

**Before writing any code or CMake, check if the tooling already handles it:**

```bash
python3 scripts/tool.py lib --help       # Library management
python3 scripts/tool.py sol --help       # Project orchestration
python3 scripts/tool.py build --help     # Build automation
python3 scripts/tool.py new --help       # Project creation wizard
python3 scripts/tool.py generate --help  # Code generation with profiles
python3 scripts/tool.py license --help   # License recommendation
```

## Creating a New Project

```bash
python3 scripts/tool.py new MyProject               # interactive wizard
python3 scripts/tool.py new MyProject --non-interactive  # CI-friendly defaults
python3 scripts/tool.py generate --profile library   # profile-based generation
python3 scripts/tool.py generate --profile minimal --with ci --without fuzz  # fine-tuned
python3 scripts/tool.py generate --explain           # preview effective settings
```

Profiles: `full` (default), `minimal`, `library`, `app`, `embedded`

## Adding a Library

```bash
python3 scripts/tool.py lib add my_lib               # normal
python3 scripts/tool.py lib add my_lib --header-only # header-only
python3 scripts/tool.py lib add my_lib --interface   # interface target
python3 scripts/tool.py lib add my_lib --template singleton  # pattern
python3 scripts/tool.py lib deps my_lib --add-url https://github.com/fmtlib/fmt@10.2.1
python3 scripts/tool.py lib export my_lib            # find_package support
```

## Validation (run after every change)

```bash
python3 scripts/tool.py build check --no-sync
```

## Documentation Governance

- **`docs/PLANS.md`** = upcoming/active work only. **`docs/CAPABILITIES.md`** = completed features.
- When a feature is done: move its entry from PLANS.md → CAPABILITIES.md and delete it from PLANS.md.
- New planned work goes into PLANS.md first.

## Mandatory Rules

- Every library needs: `CMakeLists.txt`, `README.md`, `include/<n>/`, `docs/`
- Normal libs also need: `src/<n>.cpp`, `tests/unit/<n>/`
- All CMake must be target-scoped — no global flags
- Never touch `external/` directly
- Never remove presets from `CMakePresets.json`
- C++ standard: use `target_generate_build_info` for per-lib versioning

## Module Splitting Guidelines

- **Conservative modularization:** When refactoring or splitting code into modules, avoid excessive fragmentation. Keep related functionality together unless there is a clear, testable boundary that benefits from separation.
- **Avoid the "lowest common denominator" trap:** Don't split only to satisfy minimal reuse — prefer cohesive modules that reduce complexity and cognitive overhead.
- **Agent rule:** Agents should prefer conservative grouping by default; when in doubt, leave code together and ask the maintainer before further splitting.

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
