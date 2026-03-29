# Dependencies

## Mandatory

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

## Optional

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
