# Building

## VS Code

Install the CMake Tools extension, then:

| Action | How |
|---|---|
| Select preset | Click "[No Preset]" in the status bar → choose e.g. `gcc-debug-static-x86_64` |
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

## CMake Presets (terminal)

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

## CMake without presets

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

## tool.py automation (unified CLI)

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

## Build a single app or library

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
