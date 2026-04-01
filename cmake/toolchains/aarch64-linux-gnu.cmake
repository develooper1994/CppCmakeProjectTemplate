# cmake/toolchains/aarch64-linux-gnu.cmake
# Cross-compilation toolchain for AArch64 (ARM64) Linux.
# Targets: Raspberry Pi 4/5, NVIDIA Jetson, rock64, Orange Pi 5, etc.
#
# Requirements:
#   sudo apt install gcc-aarch64-linux-gnu g++-aarch64-linux-gnu binutils-aarch64-linux-gnu
#
# Usage:
#   cmake --preset gcc-release-static-aarch64  (defined in CMakePresets.json)
#   # or manually:
#   cmake -DCMAKE_TOOLCHAIN_FILE=cmake/toolchains/aarch64-linux-gnu.cmake \
#         -B build/aarch64 -S .

set(CMAKE_SYSTEM_NAME    Linux)
set(CMAKE_SYSTEM_PROCESSOR aarch64)

set(CMAKE_C_COMPILER   aarch64-linux-gnu-gcc)
set(CMAKE_CXX_COMPILER aarch64-linux-gnu-g++)
set(CMAKE_AR           aarch64-linux-gnu-ar)
set(CMAKE_RANLIB       aarch64-linux-gnu-ranlib)
set(CMAKE_STRIP        aarch64-linux-gnu-strip)

# sysroot — use default Ubuntu cross-sysroot
# Override: -DCMAKE_SYSROOT=/path/to/custom/sysroot
if(NOT CMAKE_SYSROOT)
    set(CMAKE_SYSROOT /usr/aarch64-linux-gnu)
endif()

set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)

# Verify toolchain is available
find_program(_aarch64_cc aarch64-linux-gnu-gcc)
if(NOT _aarch64_cc)
    message(FATAL_ERROR
        "aarch64-linux-gnu-gcc not found.\n"
        "Install: sudo apt install gcc-aarch64-linux-gnu g++-aarch64-linux-gnu\n"
    )
endif()
unset(_aarch64_cc)

message(STATUS "[Toolchain] AArch64 Linux GNU — ${CMAKE_C_COMPILER}")
