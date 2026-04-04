# Getting Started with CppCmakeProjectTemplate

## Prerequisites

- C++ compiler (GCC 11+, Clang 14+, or MSVC 2022+)
- CMake 3.25+
- Python 3.10+
- Ninja (recommended)

## Building

```bash
# Clone and enter
git clone <repository-url>
cd CppCmakeProjectTemplate

# Setup development environment
python3 scripts/tool.py setup --install

# Build
python3 scripts/tool.py build

# Run tests
python3 scripts/tool.py build check --no-sync
```

## Project Structure

```
apps/           Executable applications
libs/           Libraries (each independent, versioned)
tests/          Test suites (unit, fuzz)
cmake/          CMake modules and toolchains
scripts/        Build automation and tooling
docs/           Documentation
```

## Next Steps

- Read the [API Reference](api-reference.md) for library documentation
- See [Contributing](contributing.md) to contribute to the project
