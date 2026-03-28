# C++ CMake Project Template Master Generator Prompt

**Role**: Senior C++ Software Architect & Build System Engineer.
**Goal**: Create a professional, multi-target, cross-platform C++ project template from scratch.

---

## 🏗 MANDATORY ARCHITECTURE

Create the following directory structure:

- `libs/` (Internal libraries)
- `apps/` (Executable applications)
- `external/` (Isolated 3rd party code)
- `tests/unit/` (GoogleTest suites)
- `cmake/` (Modules for Warnings, BuildInfo, Coverage)
- `cmake/toolchains/` (Cross-compilation examples)
- `scripts/` (Python/Bash automation)
- `docs/` (Project documentation)
- `.vscode/` (GUI configuration)
- `.github/workflows/` (CI/CD)

---

## 🛠 TECHNICAL REQUIREMENTS

1. **CMake 3.25+**: Use target-based design. No global `include_directories` or `add_definitions`.
2. **Cross-Platform**: Support Windows (MSVC), Linux (GCC/Clang), and macOS.
3. **Strict Warnings**: Implement a robust warning-as-errors policy in `cmake/ProjectOptions.cmake`.
4. **Static/Dynamic Linking**: Use `GenerateExportHeader` to professionally support both `BUILD_SHARED_LIBS=ON` and `OFF`.
5. **Presets**: `CMakePresets.json` must define `<compiler>-<type>-<linking>-<arch>` variants.
6. **Dependency Management**: Support **Vcpkg** (`vcpkg.json`), **Conan** (`conanfile.py`), and **FetchContent**.
7. **Quality Guard**: Integrate **GoogleTest**, **LCOV/GCOV** Coverage, and **.clang-format**.
8. **Automation**: Provide `scripts/tool.py` (Unified CLI) and `scripts/deploy.py` (Remote SSH).
9. **VS Code Integration**:
    - `tasks.json`: Automate Build, Test, Coverage, and Deploy.
    - `launch.json`: Local and Remote GDBServer debugging templates.
10. **Metadata**: Generate a `BuildInfo.h` header using Git metadata (Hash, Branch, Version).

---

## 📝 IMPLEMENTATION STEPS

1. **Initialize**: Create all directories.
2. **CMake Core**: Write root `CMakeLists.txt` with standard options (`WERROR`, `UNIT_TESTS`, `COVERAGE`).
3. **CMake Modules**:
    - `ProjectOptions.cmake` (Strict warnings for MSVC/GCC/Clang).
    - `BuildInfo.cmake` (Git metadata extraction).
    - `CodeCoverage.cmake` (LCOV/GCOV targets).
4. **Example Targets**:
    - A library (`libs/dummy_lib`) with visibility control and an export header.
    - An app (`apps/main_app`) that prints Git info and uses the library.
    - A unit test (`tests/unit/dummy_lib`) using GoogleTest.
5. **Presets & Configs**: Write `CMakePresets.json`, `.vscode/settings.json`, and `.clang-format`.
6. **CI/CD**: Create `.github/workflows/ci.yml` for Linux and Windows builds.
7. **Documentation**: Write a comprehensive `README.md` explaining VS Code GUI and Terminal usage.
8. **License**: Add MIT License.

---

## 🚀 EXECUTION

Proceed now to generate all files following this blueprint. Smallest safe changes first, verify build at each step.
