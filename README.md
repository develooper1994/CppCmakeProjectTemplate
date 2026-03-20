# C++ CMake Project Template

A professional, multi-target (solution-style) C++ project template built with Modern CMake (3.25+), strict compiler warnings, integrated unit testing, and automated documentation.

## Features
- **Modern CMake**: Target-based design with system-wide presets.
- **Strict Warnings**: High-quality code via rigorous compiler checks.
- **Dependency Isolation**: Isolated vendor code (FetchContent/SYSTEM).
- **Automated Metadata**: Git-integrated build information (hash, branch, version).
- **Unit Testing**: Pre-configured with GoogleTest.
- **AI-Ready**: Built-in instructions for AI agents (GitHub Copilot, Cursor).

## Getting Started
### Prerequisites
- CMake 3.25+
- A C++17 compatible compiler (GCC, Clang, MSVC)
- Ninja or Make

### Quick Start
```bash
# Clone the repository
git clone <url>
cd CppCmakeProjectTemplate

# Build with default preset (gcc-debug)
./scripts/build.sh

# Run the application
./build/gcc-debug/apps/main_app/main_app

# Run tests
cd build/gcc-debug && ctest
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
