# cmake/toolchains/powerpc64le-linux-gnu.cmake
# Cross-compilation toolchain for PowerPC 64-bit Little-Endian Linux.
# Targets: IBM POWER8/9/10 servers, some HPC and enterprise workloads.
#
# Requirements:
#   sudo apt install gcc-powerpc64le-linux-gnu g++-powerpc64le-linux-gnu binutils-powerpc64le-linux-gnu
#
# Usage:
#   cmake --preset gcc-release-static-powerpc64le-linux-gnu
#   # or manually:
#   cmake -DCMAKE_TOOLCHAIN_FILE=cmake/toolchains/powerpc64le-linux-gnu.cmake \
#         -B build/ppc64le -S .

set(CMAKE_SYSTEM_NAME    Linux)
set(CMAKE_SYSTEM_PROCESSOR ppc64le)

set(CMAKE_C_COMPILER   powerpc64le-linux-gnu-gcc)
set(CMAKE_CXX_COMPILER powerpc64le-linux-gnu-g++)
set(CMAKE_AR           powerpc64le-linux-gnu-ar)
set(CMAKE_RANLIB       powerpc64le-linux-gnu-ranlib)
set(CMAKE_STRIP        powerpc64le-linux-gnu-strip)

if(NOT CMAKE_SYSROOT)
    set(CMAKE_SYSROOT /usr/powerpc64le-linux-gnu)
endif()

set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)

# Verify toolchain is available
find_program(_ppc64le_cc powerpc64le-linux-gnu-gcc)
if(NOT _ppc64le_cc)
    message(FATAL_ERROR
        "powerpc64le-linux-gnu-gcc not found.\n"
        "Install: sudo apt install gcc-powerpc64le-linux-gnu g++-powerpc64le-linux-gnu\n"
    )
endif()
unset(_ppc64le_cc)

message(STATUS "[Toolchain] PowerPC64LE Linux GNU — ${CMAKE_C_COMPILER}")
