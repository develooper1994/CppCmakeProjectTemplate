# C++ CMake Project Template

A professional, multi-target (solution-style) C++ project template built with Modern CMake (3.25+), strict compiler warnings, integrated unit testing, and automated documentation.

## Features
- **Cross-Platform**: Full support for Windows (MSVC), Linux (GCC/Clang), and macOS (Clang).
- **Modern CMake**: Target-based design with system-wide presets.
- **Dependency Management**: Integrated support for **Vcpkg**, **Conan**, and **FetchContent**.
- **Remote Debugging**: Pre-configured VS Code templates for **GDBServer** support.
- **Strict Warnings**: High-quality code via rigorous compiler checks.
- **Dependency Isolation**: Isolated vendor code (FetchContent/SYSTEM).
- **Automated Metadata**: Git-integrated build information (hash, branch, version).
- **Unit Testing**: Pre-configured with GoogleTest.
- **Code Coverage**: Integrated coverage reporting via `lcov/gcov`.
- **Docker Ready**: Pre-configured development environment with `Dockerfile`.
- **AI-Ready**: Built-in instructions for AI agents (GitHub Copilot, Cursor).

## Choosing a Dependency Manager
You can manage external libraries in three ways:
1.  **Vcpkg**: Best for Windows/Visual Studio. Edit `vcpkg.json` and build with `-DCMAKE_TOOLCHAIN_FILE=[vcpkg_path]/scripts/buildsystems/vcpkg.cmake`.
2.  **Conan**: Best for complex corporate projects. Run `conan install . --output-folder=build --build=missing` then use the generated toolchain.
3.  **FetchContent**: Best for simple/header-only libs. Integrated directly into `tests/CMakeLists.txt`.

## Getting Started
...
# Generate Code Coverage Report (Linux only)
cmake --preset gcc-debug-static-x86_64 -DENABLE_COVERAGE=ON
cmake --build --preset gcc-debug-static-x86_64 --target coverage_report

# Remote Debugging
1. Open VS Code.
2. Select "Remote Debug (GDBServer)" from the debug menu.
3. Update `miDebuggerServerAddress` in `.vscode/launch.json` to your target host.
```

## Structure
- `libs/`: Internal reusable libraries.
- `apps/`: Application executables.
- `external/`: Vendor code (Isolated).
- `tests/`: Unit and integration tests.
- `cmake/`: Custom modules and toolchains.
- `scripts/`: Build and clean automation.
- `docs/`: Project documentation.

## License
MIT (or your chosen license)
