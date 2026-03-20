# C++ CMake Project Template

A professional, multi-target (solution-style) C++ project template built with Modern CMake (3.25+), strict compiler warnings, integrated unit testing, and automated documentation.

## Features
- **Cross-Platform**: Full support for Windows (MSVC), Linux (GCC/Clang), and macOS (Clang).
- **Modern CMake**: Target-based design with system-wide presets.
- **Strict Warnings**: High-quality code via rigorous compiler checks.
- **Dependency Isolation**: Isolated vendor code (FetchContent/SYSTEM).
- **Automated Metadata**: Git-integrated build information (hash, branch, version).
- **Unit Testing**: Pre-configured with GoogleTest.
- **Code Coverage**: Integrated coverage reporting via `lcov/gcov`.
- **Docker Ready**: Pre-configured development environment with `Dockerfile`.
- **AI-Ready**: Built-in instructions for AI agents (GitHub Copilot, Cursor).

## Getting Started
### Prerequisites
- CMake 3.25+
- A C++17 compatible compiler (GCC, Clang, MSVC)
- Ninja or Make (optional for Windows as MSBuild is supported)
- Python 3 (for cross-platform scripts)
- Docker (optional, for isolated environment)

### Quick Start
```bash
# Clone the repository
git clone <url>
cd CppCmakeProjectTemplate

# Build with cross-platform script (Auto-detects OS)
python3 scripts/build.py

# Or use CMake Presets directly
cmake --preset gcc-debug-static-x86_64

# Generate Code Coverage Report (Linux only)
cmake --preset gcc-debug-static-x86_64 -DENABLE_COVERAGE=ON
cmake --build --preset gcc-debug-static-x86_64 --target coverage_report
# Output: build/gcc-debug-static-x86_64/coverage_report/index.html

# Run within Docker
docker build -t cpp-template .
docker run -it --rm -v $(pwd):/workspace cpp-template
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
