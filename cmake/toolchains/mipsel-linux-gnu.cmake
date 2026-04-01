# cmake/toolchains/mipsel-linux-gnu.cmake
# Cross-compilation toolchain for MIPS Little-Endian 32-bit Linux.
# Targets: OpenWrt routers, Ingenic SoCs, some IoT/networking devices.
#
# Requirements:
#   sudo apt install gcc-mipsel-linux-gnu g++-mipsel-linux-gnu binutils-mipsel-linux-gnu
#
# Usage:
#   cmake --preset gcc-release-static-mipsel-linux-gnu
#   # or manually:
#   cmake -DCMAKE_TOOLCHAIN_FILE=cmake/toolchains/mipsel-linux-gnu.cmake \
#         -B build/mipsel -S .

set(CMAKE_SYSTEM_NAME    Linux)
set(CMAKE_SYSTEM_PROCESSOR mipsel)

set(CMAKE_C_COMPILER   mipsel-linux-gnu-gcc)
set(CMAKE_CXX_COMPILER mipsel-linux-gnu-g++)
set(CMAKE_AR           mipsel-linux-gnu-ar)
set(CMAKE_RANLIB       mipsel-linux-gnu-ranlib)
set(CMAKE_STRIP        mipsel-linux-gnu-strip)

if(NOT CMAKE_SYSROOT)
    set(CMAKE_SYSROOT /usr/mipsel-linux-gnu)
endif()

set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)

# Verify toolchain is available
find_program(_mipsel_cc mipsel-linux-gnu-gcc)
if(NOT _mipsel_cc)
    message(FATAL_ERROR
        "mipsel-linux-gnu-gcc not found.\n"
        "Install: sudo apt install gcc-mipsel-linux-gnu g++-mipsel-linux-gnu\n"
    )
endif()
unset(_mipsel_cc)

message(STATUS "[Toolchain] MIPS Little-Endian Linux GNU — ${CMAKE_C_COMPILER}")
