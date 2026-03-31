# Dependencies

## Mandatory

| Dependency | Min Version | Install (Ubuntu) |
|---|---|---|
| [CMake](https://cmake.org/) | 3.25+ | `sudo apt install cmake` |
| [Ninja](https://ninja-build.org/) | any | `sudo apt install ninja-build` |
| [GCC](https://gcc.gnu.org/) **or** [Clang](https://clang.llvm.org/) **or** [MSVC](https://visualstudio.microsoft.com/) | GCC 10+ / Clang 12+ / VS 2022 | `sudo apt install build-essential` |
| [Python](https://www.python.org/) | 3.8+ | `sudo apt install python3` |
| [Git](https://git-scm.com/) | any | `sudo apt install git` |

```bash
# Check and auto-install mandatory deps
python3 scripts/install_deps.py --install

# Check all (including optional)
python3 scripts/install_deps.py --all
```

## Python Packages

| Dependency | Purpose | Install |
|---|---|---|
| [Jinja2](https://palletsprojects.com/p/jinja/) | Templating for config files | `pip install Jinja2` |
| [conan](https://conan.io/) | C++ package manager | `pip install conan` |
| [textual](https://textual.textualize.io/) | TUI framework for interactive CLI | `pip install textual` |
| [ruff](https://github.com/charliermarsh/ruff) | Python linter | `pip install ruff` |
| [pytest](https://docs.pytest.org/) | Python testing framework | `pip install pytest` |
| [mypy](http://mypy-lang.org/) | Static type checking | `pip install mypy` |

## Optional

| Dependency | Purpose | Install (Ubuntu) |
|---|---|---|
| [clang](https://clang.llvm.org/) / [clang-tidy](https://clang.llvm.org/extra/clang-tidy/) | Alternative compiler + static analysis | `sudo apt install clang clang-tidy` |
| [clang-format](https://clang.llvm.org/docs/ClangFormat.html) | C++ code formatting | `sudo apt install clang-format` |
| [cppcheck](http://cppcheck.sourceforge.net/) | Additional static analysis | `sudo apt install cppcheck` |
| [ccache](https://ccache.dev/) | Build caching | `sudo apt install ccache` |
| [vcpkg](https://vcpkg.io/) | C++ package manager | `git clone https://github.com/microsoft/vcpkg.git && ./vcpkg/bootstrap-vcpkg.sh` |
| [pre-commit](https://pre-commit.com/) | Git hooks | `pip install pre-commit` |
| [cmake-format](https://github.com/cheshirekow/cmake_format) | CMake code formatting | `pip install cmake-format` |
| [lcov](http://ltp.sourceforge.net/coverage/lcov.php) | Coverage HTML reports | `sudo apt install lcov` |
| [Doxygen](https://www.doxygen.nl/) | API documentation | `sudo apt install doxygen` |
| [Qt 5/6](https://www.qt.io/) | GUI app (`ENABLE_QT=ON`) | `sudo apt install qt6-base-dev` |
| [Boost](https://www.boost.org/) | Boost libraries (`ENABLE_BOOST=ON`) | `sudo apt install libboost-all-dev` |
| crossbuild-essential-i386 | x86 cross-compile (i686-linux-gnu-gcc) | `sudo apt install crossbuild-essential-i386` |
| arm-none-eabi-gcc | Embedded ARM preset | `sudo apt install gcc-arm-none-eabi` |
| [Node.js](https://nodejs.org/) + [npm](https://www.npmjs.com/) | VS Code extension build | `sudo apt install nodejs npm` |
| [rsync](https://rsync.samba.org/) | Remote deploy | `sudo apt install rsync` |
| [afl++](https://aflplus.plus/) | Fuzz testing | `sudo apt install afl++` |
| [libFuzzer](https://llvm.org/docs/LibFuzzer.html) | Fuzz testing | Included with Clang |
| [Valgrind](https://valgrind.org/) | Memory debugging | `sudo apt install valgrind` |
| [AddressSanitizer](https://clang.llvm.org/docs/AddressSanitizer.html) | Memory error detection | Included with Clang |
| [UndefinedBehaviorSanitizer](https://clang.llvm.org/docs/UndefinedBehaviorSanitizer.html) | UB detection | Included with Clang |
| [GoLang](https://golang.org/) | OSV Scanner | `sudo apt install golang` |
| [osv-scanner](https://github.com/google/osv-scanner) | CVE scanning | `go install github.com/google/osv-scanner/v2/cmd/osv-scanner@latest` |

Test frameworks are **auto-downloaded** via CMake FetchContent — no manual install needed.
