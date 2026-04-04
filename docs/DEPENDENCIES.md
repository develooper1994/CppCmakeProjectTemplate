# Dependencies

> **Quick Check:** Run `python3 scripts/tool.py setup --check` to verify all dependencies at once.
>
> **Install Missing:** Run `python3 scripts/tool.py setup --do-install --all` to install system packages.

---

## 1. Critical Build Tools (required)

| Dependency | Min Version | Ubuntu | macOS (Homebrew) | Windows |
|---|---|---|---|---|
| [CMake](https://cmake.org/) | 3.25+ | `sudo apt install cmake` | `brew install cmake` | `winget install Kitware.CMake` |
| [Ninja](https://ninja-build.org/) | any | `sudo apt install ninja-build` | `brew install ninja` | `winget install Ninja-build.Ninja` |
| [Git](https://git-scm.com/) | any | `sudo apt install git` | `brew install git` | `winget install Git.Git` |
| [Python](https://www.python.org/) | 3.8+ | `sudo apt install python3` | `brew install python` | `winget install Python.Python.3.12` |

## 2. Compilers (at least one required)

| Compiler | Min Version | Ubuntu | macOS | Windows |
|---|---|---|---|---|
| [GCC](https://gcc.gnu.org/) | 10+ | `sudo apt install build-essential` | N/A | MinGW or WSL |
| [Clang](https://clang.llvm.org/) | 12+ | `sudo apt install clang` | Xcode CLT | `winget install LLVM.LLVM` |
| [MSVC](https://visualstudio.microsoft.com/) | VS 2022 | N/A | N/A | Visual Studio 2022 |

## 3. Installer Tools (recommended)

These tools are themselves dependencies — needed to install other dependencies.

| Tool | Purpose | Ubuntu | macOS | Windows |
|---|---|---|---|---|
| pip3 | Python package installer | `sudo apt install python3-pip` | Included with Python | Included with Python |
| curl | HTTP downloads | `sudo apt install curl` | `brew install curl` | Included |
| wget | HTTP downloads | `sudo apt install wget` | `brew install wget` | `winget install wget` |

## 4. Python Packages — Runtime

These packages are used by the `scripts/` tooling at runtime.

| Package | Purpose | Install |
|---|---|---|
| [Jinja2](https://palletsprojects.com/p/jinja/) | Template rendering for generated files | `pip install Jinja2` |
| [tomli](https://github.com/hukkin/tomli) | TOML parsing (Python < 3.11 only) | `pip install tomli` |
| [pyyaml](https://pyyaml.org/) | YAML config support | `pip install pyyaml` |

> **Note:** Python 3.11+ includes `tomllib` in the stdlib, so `tomli` is only needed for older Python versions.

## 5. Python Packages — Development

| Package | Purpose | Install |
|---|---|---|
| [pytest](https://docs.pytest.org/) | Test framework | `pip install pytest` |
| [pytest-cov](https://pytest-cov.readthedocs.io/) | Coverage reporting | `pip install pytest-cov` |
| [ruff](https://github.com/astral-sh/ruff) | Python linter & formatter | `pip install ruff` |
| [conan](https://conan.io/) | C++ package manager | `pip install conan` |
| [textual](https://textual.textualize.io/) | TUI framework | `pip install textual` |
| [mypy](http://mypy-lang.org/) | Static type checking | `pip install mypy` |

```bash
# Install all dev dependencies at once:
pip install -r requirements-dev.txt
```

## 6. Optional Tools — Code Quality & Documentation

| Tool | Purpose | Ubuntu | macOS | Windows |
|---|---|---|---|---|
| [ccache](https://ccache.dev/) | Build caching | `sudo apt install ccache` | `brew install ccache` | `winget install ccache.ccache` |
| [clang-format](https://clang.llvm.org/docs/ClangFormat.html) | C++ formatting | `sudo apt install clang-format` | `brew install clang-format` | `winget install LLVM.LLVM` |
| [clang-tidy](https://clang.llvm.org/extra/clang-tidy/) | Static analysis | `sudo apt install clang-tidy` | `brew install llvm` | `winget install LLVM.LLVM` |
| [cppcheck](http://cppcheck.sourceforge.net/) | Additional static analysis | `sudo apt install cppcheck` | `brew install cppcheck` | `winget install Cppcheck.Cppcheck` |
| [doxygen](https://www.doxygen.nl/) | API documentation | `sudo apt install doxygen` | `brew install doxygen` | `winget install DimitriVanHeesch.Doxygen` |
| [gcovr](https://gcovr.com/) | Coverage reports | `sudo apt install gcovr` | `brew install gcovr` | `pip install gcovr` |
| [lcov](http://ltp.sourceforge.net/coverage/lcov.php) | Coverage HTML | `sudo apt install lcov` | `brew install lcov` | N/A |
| [gitleaks](https://github.com/gitleaks/gitleaks) | Secret scanning | `sudo apt install gitleaks` | `brew install gitleaks` | `winget install Gitleaks.Gitleaks` |

## 7. Optional Tools — Platform-Specific

| Tool | Purpose | Ubuntu | macOS | Windows |
|---|---|---|---|---|
| [Valgrind](https://valgrind.org/) | Memory debugging | `sudo apt install valgrind` | N/A (Linux only) | N/A |
| [perf](https://perf.wiki.kernel.org/) | Performance profiling | `sudo apt install linux-tools-generic` | N/A | N/A |
| [Docker](https://www.docker.com/) | Containerized builds | `sudo apt install docker.io` | Docker Desktop | Docker Desktop |
| [osv-scanner](https://github.com/google/osv-scanner) | CVE scanning | `go install github.com/google/osv-scanner/v2/cmd/osv-scanner@latest` | Same | Same |

## 8. Optional Libraries & Frameworks

| Library | Purpose | CMake Flag | Ubuntu |
|---|---|---|---|
| [Qt 5/6](https://www.qt.io/) | GUI applications | `ENABLE_QT=ON` | `sudo apt install qt6-base-dev` |
| [Boost](https://www.boost.org/) | Utility libraries | `ENABLE_BOOST=ON` | `sudo apt install libboost-all-dev` |

## 9. Cross-Compilation & Embedded

| Toolchain | Purpose | Ubuntu |
|---|---|---|
| crossbuild-essential-i386 | x86 cross-compile | `sudo apt install crossbuild-essential-i386` |
| arm-none-eabi-gcc | Embedded ARM builds | `sudo apt install gcc-arm-none-eabi` |
| [Emscripten](https://emscripten.org/) | WebAssembly builds | `emsdk install latest` |

## 10. Extension Build

| Tool | Purpose | Install |
|---|---|---|
| [Node.js](https://nodejs.org/) + npm | VS Code extension packaging | `sudo apt install nodejs npm` |
| [vsce](https://github.com/microsoft/vscode-vsce) | Extension bundler | `npm install -g @vscode/vsce` |

---

## Quick Reference

```bash
# Check all dependencies (categorized report)
python3 scripts/tool.py setup --check

# Check a specific category
python3 scripts/tool.py setup --check --category critical_build

# Show install commands for missing packages
python3 scripts/tool.py setup --install --all

# Auto-install missing packages
python3 scripts/tool.py setup --do-install --all

# Create Python venv + install dev packages
python3 scripts/tool.py setup --env --install-env

# Full project health check
python3 scripts/tool.py sol doctor
```

> **Note:** Test frameworks (GoogleTest, Google Benchmark) are **auto-downloaded** via CMake FetchContent — no manual install needed.
