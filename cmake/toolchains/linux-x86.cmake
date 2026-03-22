# cmake/toolchains/linux-x86.cmake
# 32-bit x86 cross-compilation on x86_64 Linux.
#
# Requirements (crossbuild-essential approach — recommended):
#   sudo apt install crossbuild-essential-i386
#   Provides: i686-linux-gnu-gcc, i686-linux-gnu-g++
#
# Alternative (multilib, NOT recommended — causes -m32 duplication issues):
#   sudo apt install gcc-multilib g++-multilib
#
# Usage: referenced by CMakePresets.json gcc/clang-*-x86 presets via
#   "toolchainFile": "${sourceDir}/cmake/toolchains/linux-x86.cmake"

set(CMAKE_SYSTEM_NAME    Linux)
set(CMAKE_SYSTEM_PROCESSOR i686)

set(CMAKE_C_COMPILER   i686-linux-gnu-gcc)
set(CMAKE_CXX_COMPILER i686-linux-gnu-g++)

# Sysroot: use the host sysroot for now (crossbuild-essential sets up the
# required 32-bit libraries under /usr/i686-linux-gnu)
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)

# Verify toolchain availability at configure time
find_program(_cc_found i686-linux-gnu-gcc)
if(NOT _cc_found)
    message(FATAL_ERROR
        "i686-linux-gnu-gcc not found.\n"
        "Install with: sudo apt install crossbuild-essential-i386\n"
    )
endif()
unset(_cc_found)
