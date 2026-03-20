# Professional C++ CMake Project Template

A world-class, multi-target C++ project skeleton. Designed for high-performance applications with a focus on **Cross-Platform** compatibility, **Zero-Terminal** VS Code workflows, and **AI-Assisted** development.

---

## 🚀 Key Features

-   **🌍 Cross-Platform**: Native support for Windows (MSVC), Linux (GCC/Clang), and macOS (AppleClang).
-   **🛠 Modern CMake (3.25+)**: Pure target-based design. No global flags. No hacks.
-   **🖱 VS Code Optimized**: Full GUI integration. Build, Test, Debug, and Deploy without typing a single command.
-   **📦 Dependency Management**: Triple-threat support for **Vcpkg**, **Conan**, and **FetchContent**.
-   **🧪 Quality Guard**: Pre-configured **GoogleTest**, **Strict Warnings-as-Errors**, and **LCOV/GCOV** Coverage reports.
-   **🐳 Docker Ready**: Instant development environment via the included `Dockerfile`.
-   **🚀 Deploy Ready**: Automated packaging via **CPack** (.deb, .zip, .tar.gz) and **Remote SSH Deployment** scripts.
-   **🤖 AI-Native**: Structured for GitHub Copilot, Cursor, and Gemini CLI with embedded instruction sets.

---

## 💻 Usage: The VS Code Way (Recommended)

This template is designed to be used primarily through the VS Code interface:

1.  **Open Project**: Open the root folder in VS Code.
2.  **Select Preset**: Click on the **"CMake: [No Preset Selected]"** button in the bottom status bar.
    *   Choose `gcc-debug-static-x86_64` for Linux.
    *   Choose `msvc-debug-static-x64` for Windows.
3.  **Build**: Click the **Build** button in the status bar (or press `F7`).
4.  **Debug**: Press `F5` to start debugging the `main_app`.
5.  **Test**: Click the **Test** button in the status bar to run GoogleTests.
6.  **Advanced Tasks**: Press `Ctrl+Shift+P` -> `Tasks: Run Task`:
    *   `Project: Generate Coverage Report`: View how much of your code is tested.
    *   `Project: Package (CPack)`: Generate installers/archives for distribution.
    *   `Project: Remote Deploy`: Send your binaries to a remote server via SSH.

---

## ⌨️ Usage: The Terminal Way

For CI/CD or power users, use the provided Python/Bash automation:

```bash
# 1. Build (Auto-detects OS and Compiler)
python3 scripts/build.py

# 2. Run Application
./build/gcc-debug-static-x86_64/apps/main_app/main_app

# 3. Run Tests
cd build/gcc-debug-static-x86_64 && ctest

# 4. Clean Build
./scripts/clean.sh
```

---

## 🔧 Customization Points (Change These First!)

To make this project your own, search and update the following:

1.  **`CMakeLists.txt`**: Change `project(CppCmakeProjectTemplate ...)` to your project name.
2.  **`LICENSE`**: Update the copyright holder name.
3.  **`vcpkg.json` / `conanfile.py`**: Add your required third-party libraries here.
4.  **`libs/`**: Add your internal logic libraries. Follow the `dummy_lib` example.
5.  **`apps/`**: Add your entry-point applications.

---

## 📁 Directory Structure

-   `apps/`: Executable application entry points.
-   `libs/`: Reusable internal C++ libraries.
-   `external/`: Isolated 3rd party code (Never modify files here).
-   `tests/`: Unit and Integration tests using GoogleTest.
-   `cmake/`: Build system modules (Warnings, Coverage, Versioning).
-   `scripts/`: Cross-platform automation (Build, Clean, Deploy).
-   `.github/`: CI/CD workflows and AI Agent instructions.

---

## ⚖️ License
Licensed under the [MIT License](LICENSE).
