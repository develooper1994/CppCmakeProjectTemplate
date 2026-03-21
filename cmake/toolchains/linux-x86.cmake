# cmake/toolchains/linux-x86.cmake
# 32-bit x86 compilation on x86_64 Linux using multilib.
#
# Requirements:
#   GCC:  sudo apt install gcc-multilib g++-multilib
#   Clang: usually works out of the box with libc6-dev-i386
#
# Usage: referenced by CMakePresets.json gcc-*-x86 and clang-*-x86 presets.
#
# NOTE: We intentionally do NOT set CMAKE_SYSTEM_NAME / CMAKE_SYSTEM_PROCESSOR
# to avoid triggering cross-compilation mode, which would break system library
# discovery. Instead we use _INIT variables so all linker stages stay in sync.

set(CMAKE_C_FLAGS_INIT            "-m32")
set(CMAKE_CXX_FLAGS_INIT          "-m32")
set(CMAKE_EXE_LINKER_FLAGS_INIT   "-m32")
set(CMAKE_SHARED_LINKER_FLAGS_INIT "-m32")
set(CMAKE_MODULE_LINKER_FLAGS_INIT "-m32")
