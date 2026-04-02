# Professional C++ CMake Project Template

[![CI](https://github.com/develooper1994/CppCmakeProjectTemplate/actions/workflows/ci.yml/badge.svg)](https://github.com/develooper1994/CppCmakeProjectTemplate/actions/workflows/ci.yml) [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE) [![CMake: 3.25+](https://img.shields.io/badge/CMake-3.25+-informational.svg)](https://cmake.org) [![C++17](https://img.shields.io/badge/C++-17-blue.svg)](https://isocpp.org/) [![Platform](https://img.shields.io/badge/Platform-Linux%20|%20Windows%20|%20macOS-lightgrey)](https://github.com/develooper1994/CppCmakeProjectTemplate)

A professional, multi-target C++ project skeleton with cross-platform presets, per-library versioning, compile-time feature detection, and full tooling automation.

## Documentation Index

The full project README has been split into focused topic pages inside the `docs/` directory. Use the links below to jump to what you need.

- **Quick Start:** [docs/QUICK_START.md](docs/QUICK_START.md)
- **Project Structure:** [docs/PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md)
- **Embedded & Cross-Compilation Guide:** [docs/EMBEDDED.md](docs/EMBEDDED.md)
- **Building:** [docs/BUILDING.md](docs/BUILDING.md)
- **Testing:** [docs/TESTING.md](docs/TESTING.md)
- **Build Settings:** [docs/BUILD_SETTINGS.md](docs/BUILD_SETTINGS.md)
- **Dependencies:** [docs/DEPENDENCIES.md](docs/DEPENDENCIES.md)
- **Library Management:** [docs/LIBRARY_MANAGEMENT.md](docs/LIBRARY_MANAGEMENT.md)
- **Plugins:** [docs/PLUGINS.md](docs/PLUGINS.md)
- **Project Orchestration:** [docs/PROJECT_ORCHESTRATION.md](docs/PROJECT_ORCHESTRATION.md)
- **Compile-time Build Info:** [docs/BUILD_INFO.md](docs/BUILD_INFO.md)
- **Starting a New Project:** [docs/STARTING_PROJECT.md](docs/STARTING_PROJECT.md)
- **CLI Usage Reference:** [docs/USAGE.md](docs/USAGE.md)
- **Performance:** [docs/PERFORMANCE.md](docs/PERFORMANCE.md)
- **CI / Quality Guards:** [docs/CI.md](docs/CI.md)
- **Capabilities Reference:** [docs/CAPABILITIES.md](docs/CAPABILITIES.md)
- **Ideas & Future Directions:** [docs/IDEAS.md](docs/IDEAS.md)

If you'd like these pages further split (for example `docs/BUILDING.md` → `docs/VS_CODE.md`, `docs/PRESETS.md`), tell me which area to subdivide next.

This repository's full documentation was long; the complete README has been moved to the `docs/README_FULL.md` file. The short quick-start is below — for all details, examples and the full reference, see the full document.

## Quick Start

```bash
# Create a new project interactively
python3 scripts/tool.py new MyProject

# Or non-interactive with defaults
python3 scripts/tool.py new MyProject --non-interactive
```

For an existing clone:

```bash
# 1. Install mandatory dependencies (Ubuntu/Debian)
python3 scripts/tool.py setup --install

# 2. Configure + build + test (auto-detects platform preset)
python3 scripts/tool.py build check

# 3. Run the example app
./build/gcc-debug-static-x86_64/apps/main_app/main_app
```

Full documentation: [docs/README_FULL.md](docs/README_FULL.md) | Plans: [docs/PLANS.md](docs/PLANS.md) | Capabilities: [docs/CAPABILITIES.md](docs/CAPABILITIES.md) | Embedded guide: [docs/EMBEDDED.md](docs/EMBEDDED.md)
