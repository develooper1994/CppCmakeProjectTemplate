# Professional C++ CMake Project Template

[![CI](https://github.com/develooper1994/CppCmakeProjectTemplate/actions/workflows/ci.yml/badge.svg)](https://github.com/develooper1994/CppCmakeProjectTemplate/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![CMake: 3.25+](https://img.shields.io/badge/CMake-3.25+-informational.svg)](https://cmake.org)
[![C++17](https://img.shields.io/badge/C++-17-blue.svg)](https://isocpp.org/)
[![Platform](https://img.shields.io/badge/Platform-Linux%20|%20Windows%20|%20macOS-lightgrey)](https://github.com/develooper1994/CppCmakeProjectTemplate)

A professional, multi-target C++ project skeleton with cross-platform presets, per-library
versioning, compile-time feature detection, and full tooling automation.

> **VS Code Extension:**
> `Ctrl+Shift+P` → *CppTemplate: Create New Project*
> [Marketplace](https://marketplace.visualstudio.com/items?itemName=develooper1994.cpp-cmake-scaffolder)

---

## Table of Contents

1. [Quick Start](#1-quick-start)
2. [Directory Structure](#2-directory-structure)
3. [Building](#3-building)
   - [VS Code](#31-vs-code)
   - [CMake Presets (terminal)](#32-cmake-presets-terminal)
   - [CMake without presets](#33-cmake-without-presets)
    - [tool.py automation (unified CLI)](#34-toolpy-automation-unified-cli)
   - [Build a single app or library](#35-build-a-single-app-or-library)
4. [Testing](#4-testing)
   - [All tests](#41-all-tests)
   - [Single library tests](#42-single-library-tests)
5. [Build Settings Reference](#5-build-settings-reference)
6. [Dependencies](#6-dependencies)
7. [Library Management](#7-library-management)
8. [Project Orchestration](#8-project-orchestration)
9. [Compile-time Build Info & Feature Flags](#9-compile-time-build-info--feature-flags)
10. [Starting a New Project](#10-starting-a-new-project)
11. [CI / Quality Guards](#11-ci--quality-guards)

---

## 1. Quick Start

```bash
# 1. Install mandatory dependencies (Ubuntu/Debian)
python3 scripts/tool.py setup --install

# 2. Configure + build + test (auto-detects platform preset)
python3 scripts/tool.py build check

# 3. Run the example app
./build/gcc-debug-static-x86_64/apps/main_app/main_app
```

---

## 2. Directory Structure

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

---

## 3. Building

### 3.1 VS Code

Install the [CMake Tools](https://marketplace.visualstudio.com/items?itemName=ms-vscode.cmake-tools) extension, then:

| Action | How |
|---|---|
| Select preset | Click **"[No Preset]"** in the status bar → choose e.g. `gcc-debug-static-x86_64` |
| Configure | `Ctrl+Shift+P` → *CMake: Configure* |
| Build whole solution | `F7` or *CMake: Build* |
| Build single target | `Ctrl+Shift+P` → *CMake: Set Build Target* → pick target → `F7` |
| Run | `Ctrl+Shift+P` → *CMake: Run Without Debugging* |
| Debug | `F5` |
| Test | Click **Tests** in the status bar (CTest integration) |

**VS Code Tasks** (`Ctrl+Shift+B` or *Terminal → Run Task*):

| Task | Action |
|---|---|
| `Project: Build` | Configure + compile default preset |
| `Project: Build + Test + Extension` | Full check pipeline |
| `Project: Clean` | Remove build artifacts |
| `Project: Clean All` | Also removes `.vsix` and `build_logs` |
| `Project: Build Extension (.vsix)` | Package VS Code extension |

### 3.2 CMake Presets (terminal)

Preset naming: `<compiler>-<type>-<link>-<arch>`

```bash
# List all available presets
cmake --list-presets

# Configure
cmake --preset gcc-debug-static-x86_64

# Build (whole solution)
cmake --build --preset gcc-debug-static-x86_64

# Build a specific target
cmake --build --preset gcc-debug-static-x86_64 --target main_app
cmake --build --preset gcc-debug-static-x86_64 --target dummy_lib
cmake --build --preset gcc-debug-static-x86_64 --target dummy_lib_tests

# Run tests (all)
ctest --preset gcc-debug-static-x86_64 --output-on-failure

# Run tests (filter by name)
ctest --preset gcc-debug-static-x86_64 -R dummy_lib --output-on-failure
```

**Common presets:**

| Preset | OS | Compiler | Type | Link |
|---|---|---|---|---|
| `gcc-debug-static-x86_64` | Linux | GCC | Debug | Static |
| `gcc-release-static-x86_64` | Linux | GCC | Release | Static |
| `gcc-relwithdebinfo-static-x86_64` | Linux | GCC | RelWithDebInfo | Static |
| `clang-debug-static-x86_64` | Linux | Clang | Debug | Static |
| `msvc-debug-static-x64` | Windows | MSVC | Debug | Static |
| `msvc-release-static-x64` | Windows | MSVC | Release | Static |
| `embedded-arm-none-eabi` | Any | arm-none-eabi-gcc | Release | Static |

### 3.3 CMake without presets

```bash
# Configure manually (no preset)
cmake -B build/manual \
    -G Ninja \
    -DCMAKE_BUILD_TYPE=Debug \
    -DBUILD_SHARED_LIBS=OFF \
    -DCMAKE_CXX_STANDARD=17

# Build whole solution
cmake --build build/manual

# Build single target
cmake --build build/manual --target main_app
cmake --build build/manual --target dummy_lib

# With extra options
cmake -B build/manual \
    -DENABLE_ASAN=ON \
    -DENABLE_CLANG_TIDY=ON \
    -DENABLE_UNIT_TESTS=ON \
    -DENABLE_GTEST=ON
cmake --build build/manual

# Shared libraries
cmake -B build/shared -DBUILD_SHARED_LIBS=ON -DCMAKE_BUILD_TYPE=Release
cmake --build build/shared
```

### 3.4 tool.py automation (unified CLI)

```bash
# Build (auto-detects platform default preset)
python3 scripts/tool.py build

# Build with specific preset
python3 scripts/tool.py build --preset clang-debug-static-x86_64

# Full pipeline: configure + build + test + extension sync
python3 scripts/tool.py build check

# Full pipeline, skip extension sync
python3 scripts/tool.py build check --no-sync

# Clean build artifacts
python3 scripts/tool.py build clean

# Clean everything including .vsix and logs
python3 scripts/tool.py build clean --all

# Build VS Code extension
python3 scripts/tool.py build extension

# Build and install extension
python3 scripts/tool.py build extension --install

# Build and publish to Marketplace
python3 scripts/tool.py build extension --publish

# Remote deploy via rsync
python3 scripts/tool.py build deploy --host user@192.168.1.10 --path /opt/myapp
```

### 3.5 Build a single app or library

```bash
# Via cmake --build --target (after configure)
cmake --build --preset gcc-debug-static-x86_64 --target main_app
cmake --build --preset gcc-debug-static-x86_64 --target dummy_lib

# Via toolsolution (auto-configures if needed)
python3 scripts/tool.py sol target build main_app
python3 scripts/tool.py sol target build dummy_lib --preset gcc-release-static-x86_64

# Via tool lib (single library only)
python3 scripts/tool.py lib test dummy_lib
```

---

## 4. Testing

### 4.1 All tests

```bash
# Using ctest preset (recommended)
ctest --preset gcc-debug-static-x86_64 --output-on-failure

# Using unified CLI (configure + build + test)
python3 scripts/tool.py build check --no-sync

# Using toolsolution (auto-configures if needed)
python3 scripts/tool.py sol test

# Via VS Code: click "Tests" in the status bar
```

**With verbose output:**

```bash
ctest --preset gcc-debug-static-x86_64 --output-on-failure --verbose

# Stop on first failure
ctest --preset gcc-debug-static-x86_64 --stop-on-failure
```

### 4.2 Single library tests

```bash
# Method 1: ctest filter by name
ctest --preset gcc-debug-static-x86_64 -R dummy_lib --output-on-failure

# Method 2: build and run the test binary directly
cmake --build --preset gcc-debug-static-x86_64 --target dummy_lib_tests
./build/gcc-debug-static-x86_64/tests/unit/dummy_lib/dummy_lib_tests

# Run with GTest filter
./build/gcc-debug-static-x86_64/tests/unit/dummy_lib/dummy_lib_tests \
    --gtest_filter="BuildInfoTest.*"

# Method 3: tool lib (builds if needed)
python3 scripts/tool.py lib test dummy_lib

# Method 4: tool sol
python3 scripts/tool.py sol test dummy_lib
```

---

## 5. Build Settings Reference

All options are passed as `-D<OPTION>=ON/OFF` to CMake or set via a preset.

### Core Build

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

### Tests

| Option | Default | Description |
|---|---|---|
| `ENABLE_UNIT_TESTS` | `ON` | Master switch — `OFF` removes all test dependencies |
| `ENABLE_GTEST` | `ON` | GoogleTest (auto-downloaded) |
| `ENABLE_CATCH2` | `OFF` | Catch2 v3 (auto-downloaded) |
| `ENABLE_BOOST_TEST` | `OFF` | Boost.Test (requires `ENABLE_BOOST=ON`) |
| QTest | auto | Enabled automatically when `ENABLE_QT=ON` |

### Sanitizers

| Option | Default | Description |
|---|---|---|
| `ENABLE_ASAN` | `OFF` | AddressSanitizer |
| `ENABLE_UBSAN` | `OFF` | UndefinedBehaviorSanitizer |
| `ENABLE_TSAN` | `OFF` | ThreadSanitizer (mutually exclusive with ASan/UBSan) |

### Static Analysis & Coverage

| Option | Default | Description |
|---|---|---|
| `ENABLE_CLANG_TIDY` | `OFF` | clang-tidy |
| `ENABLE_CPPCHECK` | `OFF` | cppcheck |
| `ENABLE_COVERAGE` | `OFF` | LCOV/GCOV HTML report |

```bash
cmake --preset gcc-debug-static-x86_64 -DENABLE_COVERAGE=ON
cmake --build --preset gcc-debug-static-x86_64 --target coverage_report
```

### Optional Frameworks

| Option | Default | Description |
|---|---|---|
| `ENABLE_QT` | `OFF` | Qt5 or Qt6 (auto-detected) |
| `ENABLE_QML` | `OFF` | Qt QML (requires `ENABLE_QT=ON`) |
| `ENABLE_BOOST` | `OFF` | Boost libraries |
| `BOOST_COMPONENTS` | `""` | Semicolon-separated: `filesystem;system` |

### MSVC Runtime

| | Static build | Shared build |
|---|---|---|
| Release | `/MT` | `/MD` |
| Debug | `/MTd` | `/MDd` |

Set automatically from `BUILD_SHARED_LIBS`. Mixing runtimes causes `LNK2038`.

---

## 6. Dependencies

### Mandatory

| Dependency | Min Version | Install (Ubuntu) |
|---|---|---|
| CMake | 3.25+ | `sudo apt install cmake` |
| Ninja | any | `sudo apt install ninja-build` |
| GCC **or** Clang **or** MSVC | GCC 10+ / Clang 12+ / VS 2022 | `sudo apt install build-essential` |
| Python | 3.8+ | `sudo apt install python3` |
| Git | any | `sudo apt install git` |

```bash
# Check and auto-install mandatory deps
python3 scripts/install_deps.py --install

# Check all (including optional)
python3 scripts/install_deps.py --all
```

### Optional

| Dependency | Purpose | Install (Ubuntu) |
|---|---|---|
| clang / clang-tidy | Alternative compiler + static analysis | `sudo apt install clang clang-tidy` |
| cppcheck | Additional static analysis | `sudo apt install cppcheck` |
| lcov | Coverage HTML reports | `sudo apt install lcov` |
| Doxygen | API documentation | `sudo apt install doxygen` |
| Qt 5/6 | GUI app (`ENABLE_QT=ON`) | `sudo apt install qt6-base-dev` |
| Boost | Boost libraries (`ENABLE_BOOST=ON`) | `sudo apt install libboost-all-dev` |
| crossbuild-essential-i386 | x86 cross-compile (i686-linux-gnu-gcc) | `sudo apt install crossbuild-essential-i386` |
| arm-none-eabi-gcc | Embedded ARM preset | `sudo apt install gcc-arm-none-eabi` |
| Node.js + npm | VS Code extension build | `sudo apt install nodejs npm` |
| rsync | Remote deploy | `sudo apt install rsync` |

Test frameworks are **auto-downloaded** via CMake FetchContent — no manual install needed.

---

## 7. Library Management

All library operations go through `scripts/tool.py lib` (use the `lib` subcommand).
**In VS Code:** `Ctrl+Shift+P` → *CppTemplate: Library Manager*

```bash
# Create a new library
python3 scripts/tool.py lib add my_lib
python3 scripts/tool.py lib add renderer --deps core,math --link-app --cxx-standard 20

# Remove a library (--delete also removes files from disk)
python3 scripts/tool.py lib remove my_lib --delete

# Rename (updates all source files, headers, and CMake references)
python3 scripts/tool.py lib rename old_name new_name

# Move to a subdirectory
python3 scripts/tool.py lib move renderer graphics/renderer

# Edit dependencies of an existing library
python3 scripts/tool.py lib deps renderer --add math --remove old_dep

# Show detailed info about a library
python3 scripts/tool.py lib info dummy_lib

# Add external dependency (FetchContent / vcpkg / conan)
python3 scripts/tool.py lib deps my_lib --add-url https://github.com/fmtlib/fmt@10.2.1
python3 scripts/tool.py lib deps my_lib --add-url https://github.com/nlohmann/json@3.11.3 --target nlohmann_json::nlohmann_json
python3 scripts/tool.py lib deps my_lib --add-url fmt --via vcpkg
python3 scripts/tool.py lib deps my_lib --add-url fmt/10.2.1 --via conan

# Build and run a single library's tests
python3 scripts/tool.py lib test dummy_lib
python3 scripts/tool.py lib test dummy_lib --preset clang-debug-static-x86_64

# List / tree / health check
python3 scripts/tool.py lib list
python3 scripts/tool.py lib tree
python3 scripts/tool.py lib doctor
```

Append `--dry-run` to any command to preview changes without applying them.

Each library gets its own independent version via `target_generate_build_info`:

```cmake
# libs/my_lib/CMakeLists.txt
target_generate_build_info(my_lib
    NAMESPACE my_lib_info
    PROJECT_VERSION "2.0.0"   # independent from solution version
)
```

---

### New Capabilities (v1.0.0+)

- **Header-only / Interface Libs:** `python3 scripts/tool.py lib add my_lib --header-only`
- **Export Config:** `python3 scripts/tool.py lib export my_lib` (creates cmake config for find_package)
- **URL Dependencies:** `python3 scripts/tool.py lib deps my_lib --add-url https://...` (FetchContent/vcpkg/conan)
- **Repo Management:** `python3 scripts/tool.py sol repo ...` (submodules & fetch deps)

## 8. Project Orchestration

**In VS Code:** `Ctrl+Shift+P` → *CppTemplate: Project Orchestrator (toolsolution)*

```bash
# List all targets (libs + apps)
python3 scripts/tool.py sol target list

# Build a single target (auto-configures if needed)
python3 scripts/tool.py sol target build main_app
python3 scripts/tool.py sol target build dummy_lib --preset gcc-release-static-x86_64

# Run tests — all or single target
python3 scripts/tool.py sol test
python3 scripts/tool.py sol test dummy_lib

# Manage presets
python3 scripts/tool.py sol preset list
python3 scripts/tool.py sol preset add --compiler gcc --type debug --link static --arch x86_64
python3 scripts/tool.py sol preset remove my-custom-preset

# Manage toolchains
python3 scripts/tool.py sol toolchain list
python3 scripts/tool.py sol toolchain add \
    --name stm32f4 --template arm-none-eabi \
    --cpu cortex-m4 --fpu fpv4-sp-d16 --gen-preset
python3 scripts/tool.py sol toolchain remove stm32f4

# C++ standard — solution-wide or per-library
python3 scripts/tool.py sol upgrade-std --std 20
python3 scripts/tool.py sol upgrade-std --std 20 --target dummy_lib
python3 scripts/tool.py sol upgrade-std --std 20 --dry-run

# View / set base preset cache variables
python3 scripts/tool.py sol config get
python3 scripts/tool.py sol config set ENABLE_ASAN ON

# Full health check
python3 scripts/tool.py sol doctor
```

---

## 9. Compile-time Build Info & Feature Flags

Every target built with `target_generate_build_info` gets a `BuildInfo.h` at compile time.
Include `ProjectInfo.h` as a single-header convenience wrapper:

```cpp
#include "ProjectInfo.h"   // BuildInfo.h + FeatureFlags.h + BuildInfoHelper.h

// Print everything (build info + git + feature flags)
BUILD_INFO_PRINT_ALL(std::cout, main_app_info);

// Short version line: "CppCmakeProjectTemplate v1.0.0 (main@abc1234)"
std::string ver = BUILD_INFO_VERSION_LINE(main_app_info);

// Access individual fields
std::cout << main_app_info::project_version << "\n";  // "1.0.0"
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
std::cout << main_app_info::project_version;   // "1.0.0"
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

---

## 10. Starting a New Project

**Option A — VS Code Extension (recommended):**

1. `Ctrl+Shift+P` → *CppTemplate: Create New Project*
2. Select target folder, enter project name.

**Option B — Terminal:**

```bash
git clone https://github.com/develooper1994/CppCmakeProjectTemplate.git MyProject
cd MyProject
python3 scripts/init_project.py --name MyProject
```

Both options rename all `CppCmakeProjectTemplate` references to your project name.

---

## 11. CI / Quality Guards

### Pre-commit hooks

```bash
python3 scripts/setup_hooks.py
```

Runs: clang-format, clang-tidy, secret scanner on every commit.

### CI matrix

Four jobs run on every push (`.github/workflows/ci.yml`):

| Job | OS | Compiler |
|---|---|---|
| `build-linux` | Ubuntu | GCC 13 |
| `build-linux-clang` | Ubuntu | Clang |
| `build-windows` | Windows | MSVC 2022 |
| `build-macos` | macOS | AppleClang |

### Manual CI simulation

```bash
python3 scripts/tool.py sol doctor
ctest --preset gcc-debug-static-x86_64 --output-on-failure
```

### TUI (Terminal User Interface)

A full-screen terminal UI wrapping all tooling:

```bash
# Install textual (one-time)
pip3 install textual --break-system-packages

# Launch TUI
python3 scripts/tui.py
```

Tabs: 🔨 Build / 📚 Libraries / ⚙ Project / ℹ Info — all operations delegate to CLI tools.

---

## ⚖️ License

Licensed under the [MIT License](LICENSE).
