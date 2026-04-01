# cmake/toolchains/x86_64-w64-mingw32.cmake
# Cross-compilation toolchain for Windows (x86_64) from Linux using MinGW-w64.
# Produces native Windows .exe binaries without a Windows host or MSVC.
#
# Requirements:
#   sudo apt install gcc-mingw-w64-x86-64 g++-mingw-w64-x86-64 binutils-mingw-w64-x86-64
#
# Usage:
#   cmake --preset gcc-release-static-x86_64-w64-mingw32
#   # or manually:
#   cmake -DCMAKE_TOOLCHAIN_FILE=cmake/toolchains/x86_64-w64-mingw32.cmake \
#         -B build/mingw64 -S .
#
# Notes:
#   - Produces .exe binaries. Wine can run them on Linux for testing.
#   - Static linking recommended to avoid MinGW runtime DLL dependencies.

set(CMAKE_SYSTEM_NAME    Windows)
set(CMAKE_SYSTEM_PROCESSOR x86_64)

set(CMAKE_C_COMPILER   x86_64-w64-mingw32-gcc)
set(CMAKE_CXX_COMPILER x86_64-w64-mingw32-g++)
set(CMAKE_RC_COMPILER  x86_64-w64-mingw32-windres)
set(CMAKE_AR           x86_64-w64-mingw32-ar)
set(CMAKE_RANLIB       x86_64-w64-mingw32-ranlib)
set(CMAKE_STRIP        x86_64-w64-mingw32-strip)

set(CMAKE_FIND_ROOT_PATH /usr/x86_64-w64-mingw32)

set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)

# Verify toolchain is available
find_program(_mingw_cc x86_64-w64-mingw32-gcc)
if(NOT _mingw_cc)
    message(FATAL_ERROR
        "x86_64-w64-mingw32-gcc not found.\n"
        "Install: sudo apt install gcc-mingw-w64-x86-64 g++-mingw-w64-x86-64\n"
    )
endif()
unset(_mingw_cc)

message(STATUS "[Toolchain] x86_64 Windows (MinGW-w64) — ${CMAKE_C_COMPILER}")
