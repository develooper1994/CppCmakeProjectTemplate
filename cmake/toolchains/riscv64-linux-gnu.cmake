# cmake/toolchains/riscv64-linux-gnu.cmake
# Cross-compilation toolchain for RISC-V 64-bit Linux (RV64GC).
# Targets: SiFive HiFive, StarFive VisionFive 2, Milk-V, QEMU riscv64.
#
# Requirements:
#   sudo apt install gcc-riscv64-linux-gnu g++-riscv64-linux-gnu binutils-riscv64-linux-gnu
#
# Usage:
#   cmake --preset gcc-release-static-riscv64-linux-gnu
#   # or manually:
#   cmake -DCMAKE_TOOLCHAIN_FILE=cmake/toolchains/riscv64-linux-gnu.cmake \
#         -B build/riscv64 -S .

set(CMAKE_SYSTEM_NAME    Linux)
set(CMAKE_SYSTEM_PROCESSOR riscv64)

set(CMAKE_C_COMPILER   riscv64-linux-gnu-gcc)
set(CMAKE_CXX_COMPILER riscv64-linux-gnu-g++)
set(CMAKE_AR           riscv64-linux-gnu-ar)
set(CMAKE_RANLIB       riscv64-linux-gnu-ranlib)
set(CMAKE_STRIP        riscv64-linux-gnu-strip)

if(NOT CMAKE_SYSROOT)
    set(CMAKE_SYSROOT /usr/riscv64-linux-gnu)
endif()

set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)

# Verify toolchain is available
find_program(_rv64_cc riscv64-linux-gnu-gcc)
if(NOT _rv64_cc)
    message(FATAL_ERROR
        "riscv64-linux-gnu-gcc not found.\n"
        "Install: sudo apt install gcc-riscv64-linux-gnu g++-riscv64-linux-gnu\n"
    )
endif()
unset(_rv64_cc)

message(STATUS "[Toolchain] RISC-V 64-bit Linux GNU (RV64GC) — ${CMAKE_C_COMPILER}")
