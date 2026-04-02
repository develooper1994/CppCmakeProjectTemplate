# Project Structure

```
CppCmakeProjectTemplate/
├── apps/
│   ├── main_app/          # Executable — links dummy_lib, prints build info
│   ├── demo_app/          # Demo executable
│   ├── extreme_app/       # Hardened (extreme profile) executable
│   └── gui_app/           # Qt GUI app (compiled only when ENABLE_QT=ON)
├── libs/
│   ├── dummy_lib/         # Example library with independent versioning
│   ├── secure_ops/        # Security-hardened library
│   └── fuzzable/          # Fuzz-testable library
├── tests/
│   └── unit/              # GoogleTest per-library test suites
├── cmake/                 # CMake modules
│   ├── BuildInfo.cmake    # Per-target build metadata generation
│   ├── BuildInfoHelper.h  # C++ helper — BUILD_INFO_PRINT_ALL macro
│   ├── FeatureFlags.cmake # Dynamic FeatureFlags.h generation
│   ├── ProjectInfo.h      # Single-include wrapper (BuildInfo + FeatureFlags)
│   ├── ProjectConfigs.cmake
│   ├── ProjectOptions.cmake
│   └── toolchains/        # arm-none-eabi, linux-x86, musl, zig-musl
├── scripts/
│   ├── tool.py            # Unified CLI (build, lib, sol, new, generate, license)
│   ├── tui.py             # Terminal UI
│   ├── core/
│   │   ├── commands/      # Core logic (build, lib, sol, generate, new, license)
│   │   ├── generator/     # Project generator (engine, wizard, profiles, manifest)
│   │   └── utils/         # Infrastructure (common.py)
│   └── plugins/           # Dynamic plugins (setup, init, hooks, ...)
├── docs/
│   └── ROADMAP.md         # Strategic roadmap & ideas
├── extension/             # VS Code extension (C++ CMake Scaffolder)
├── tool.toml              # Project configuration (single source of truth)
├── CMakeLists.txt
└── CMakePresets.json      # All platform/compiler/type/arch combinations
```
