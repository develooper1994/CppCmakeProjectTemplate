# Project Structure

```
CppCmakeProjectTemplate/
├── apps/
│   ├── main_app/          # Executable — links dummy_lib, prints build info
│   └── gui_app/           # Qt GUI app (compiled only when ENABLE_QT=ON)
├── libs/
│   └── dummy_lib/         # Example library with independent versioning
├── tests/
│   └── unit/
│       └── dummy_lib/     # GoogleTest suite for dummy_lib
├── cmake/                 # CMake modules
│   ├── BuildInfo.cmake    # Per-target build metadata generation
│   ├── BuildInfoHelper.h  # C++ helper — BUILD_INFO_PRINT_ALL macro
│   ├── FeatureFlags.cmake # Dynamic FeatureFlags.h generation
│   ├── ProjectInfo.h      # Single-include wrapper (BuildInfo + FeatureFlags)
│   ├── ProjectConfigs.cmake
│   ├── ProjectOptions.cmake
│   └── toolchains/        # arm-none-eabi, linux-x86, template-custom-gnu
├── scripts/
│   ├── tool.py            # Unified CLI entrypoint (build, lib, sol, tui, plugins)
│   ├── tui.py             # Terminal UI (callable directly or via `tool tui`)
│   ├── core/              # Command implementations (core.commands)
│   └── plugins/           # Dynamic plugins (setup, init, hooks, ...)
├── docs/
│   ├── PLANS.md           # Pending feature plans
│   └── EMBEDDED.md        # Embedded development guide
├── CMakeLists.txt
└── CMakePresets.json      # All platform/compiler/type/arch combinations
```
