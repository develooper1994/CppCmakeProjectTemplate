# cmake/toolchains/armv7-linux-gnueabihf.cmake
# Cross-compilation toolchain for ARMv7 hard-float Linux.
# Targets: Raspberry Pi 2/3 (32-bit), BeagleBone Black, i.MX6, many IoT gateways.
#
# Requirements:
#   sudo apt install gcc-arm-linux-gnueabihf g++-arm-linux-gnueabihf binutils-arm-linux-gnueabihf
#
# Usage:
#   cmake --preset gcc-release-static-armv7-linux-gnueabihf
#   # or manually:
#   cmake -DCMAKE_TOOLCHAIN_FILE=cmake/toolchains/armv7-linux-gnueabihf.cmake \
#         -B build/armv7hf -S .

set(CMAKE_SYSTEM_NAME    Linux)
set(CMAKE_SYSTEM_PROCESSOR armv7l)

set(CMAKE_C_COMPILER   arm-linux-gnueabihf-gcc)
set(CMAKE_CXX_COMPILER arm-linux-gnueabihf-g++)
set(CMAKE_AR           arm-linux-gnueabihf-ar)
set(CMAKE_RANLIB       arm-linux-gnueabihf-ranlib)
set(CMAKE_STRIP        arm-linux-gnueabihf-strip)

if(NOT CMAKE_SYSROOT)
    set(CMAKE_SYSROOT /usr/arm-linux-gnueabihf)
endif()

set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)

# Verify toolchain is available
find_program(_armhf_cc arm-linux-gnueabihf-gcc)
if(NOT _armhf_cc)
    message(FATAL_ERROR
        "arm-linux-gnueabihf-gcc not found.\n"
        "Install: sudo apt install gcc-arm-linux-gnueabihf g++-arm-linux-gnueabihf\n"
    )
endif()
unset(_armhf_cc)

message(STATUS "[Toolchain] ARMv7 Linux GNU hard-float — ${CMAKE_C_COMPILER}")
