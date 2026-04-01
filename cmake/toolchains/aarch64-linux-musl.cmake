# cmake/toolchains/aarch64-linux-musl.cmake
# Fully static ARM64 Linux builds using musl libc.
#
# Produces statically linked aarch64 binaries with no glibc dependency.
# Ideal for Alpine-based ARM64 containers (AWS Graviton, Raspberry Pi Docker).
#
# Requirements (pick one):
#
#   Option A — musl-cross-make (recommended):
#     Build an aarch64-linux-musl cross-toolchain from source.
#     See: https://github.com/richfelker/musl-cross-make
#     Provides: aarch64-linux-musl-gcc / aarch64-linux-musl-g++
#
#   Option B — Alpine Docker (native aarch64 or QEMU user-mode):
#     docker build -f docker/Dockerfile.alpine -t cpp-musl-builder .
#     docker run --platform linux/arm64 --rm -v $PWD:/workspace ...
#
#   Option C — Zig cc:
#     Use aarch64-linux-musl-zig.cmake toolchain instead (zero-install).
#
# Usage:
#   cmake --preset gcc-release-static-aarch64-linux-musl
#   # or manually:
#   cmake -DCMAKE_TOOLCHAIN_FILE=cmake/toolchains/aarch64-linux-musl.cmake \
#         -B build/aarch64-musl -S .
#
# Notes:
#   - Sanitizers (ASan, TSan, UBSan, MSan) are NOT compatible with musl.
#   - Dynamic linking is not supported (BUILD_SHARED_LIBS forced OFF).

set(CMAKE_SYSTEM_NAME    Linux)
set(CMAKE_SYSTEM_PROCESSOR aarch64)

# ---------------------------------------------------------------------------
# Compiler selection
# ---------------------------------------------------------------------------
find_program(_musl_cross_gcc  aarch64-linux-musl-gcc)
find_program(_musl_cross_gxx  aarch64-linux-musl-g++)

if(_musl_cross_gcc AND _musl_cross_gxx)
    set(CMAKE_C_COMPILER   aarch64-linux-musl-gcc)
    set(CMAKE_CXX_COMPILER aarch64-linux-musl-g++)
    message(STATUS "[Toolchain/musl] Using aarch64-linux-musl cross-toolchain")
else()
    message(FATAL_ERROR
        "No aarch64 musl toolchain found.\n"
        "Install one of:\n"
        "  (a) musl-cross-make (aarch64-linux-musl target)\n"
        "  (b) Alpine Docker with QEMU user-mode\n"
        "  (c) Zig cc: use aarch64-linux-musl-zig.cmake instead\n")
endif()

unset(_musl_cross_gcc)
unset(_musl_cross_gxx)

# ---------------------------------------------------------------------------
# Force fully static linking
# ---------------------------------------------------------------------------
set(CMAKE_EXE_LINKER_FLAGS_INIT "-static")
set(CMAKE_FIND_LIBRARY_SUFFIXES ".a")
set(BUILD_SHARED_LIBS OFF CACHE BOOL "musl toolchain forces static linking" FORCE)

option(MUSL_STATIC_PIE "Build static-PIE binaries (requires musl 1.2+)" OFF)
if(MUSL_STATIC_PIE)
    set(CMAKE_EXE_LINKER_FLAGS_INIT "-static-pie")
    message(STATUS "[Toolchain/musl] Static-PIE enabled (ASLR on static binaries)")
endif()

# ---------------------------------------------------------------------------
# Search policy
# ---------------------------------------------------------------------------
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)

# ---------------------------------------------------------------------------
# Disable sanitizers — not compatible with musl
# ---------------------------------------------------------------------------
set(ENABLE_ASAN  OFF CACHE BOOL "ASan not supported with musl" FORCE)
set(ENABLE_TSAN  OFF CACHE BOOL "TSan not supported with musl" FORCE)
set(ENABLE_UBSAN OFF CACHE BOOL "UBSan not supported with musl" FORCE)
set(ENABLE_MSAN  OFF CACHE BOOL "MSan not supported with musl" FORCE)

message(STATUS "[Toolchain] AArch64 Linux musl (fully static)")
