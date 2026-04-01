# cmake/toolchains/x86_64-linux-musl-zig.cmake
# Fully static Linux builds using Zig cc + musl libc.
#
# Zig ships with musl libc built-in, so no separate musl toolchain or
# Alpine Docker is needed.  Works on any host (Linux, macOS, Windows)
# that has `zig` in PATH.
#
# Requirements:
#   Install Zig (https://ziglang.org/download/) and ensure `zig` is in PATH.
#
# Usage:
#   cmake --preset gcc-release-static-x86_64-linux-musl-zig
#   # or manually:
#   cmake -DCMAKE_TOOLCHAIN_FILE=cmake/toolchains/x86_64-linux-musl-zig.cmake \
#         -B build/musl-zig -S .
#
# Notes:
#   - Sanitizers (ASan, TSan, UBSan, MSan) are NOT compatible with musl.
#   - Dynamic linking is not supported (BUILD_SHARED_LIBS forced OFF).
#   - Zig cc supports cross-compilation natively — no sysroot or cross-toolchain needed.
#   - For ASLR protection on static binaries, pass -DMUSL_STATIC_PIE=ON.

set(CMAKE_SYSTEM_NAME    Linux)
set(CMAKE_SYSTEM_PROCESSOR x86_64)

# ---------------------------------------------------------------------------
# Locate Zig
# ---------------------------------------------------------------------------
find_program(_zig_bin zig)
if(NOT _zig_bin)
    message(FATAL_ERROR
        "zig not found in PATH.\n"
        "Install Zig from https://ziglang.org/download/ and try again.")
endif()

# ---------------------------------------------------------------------------
# Create wrapper scripts for zig cc / zig c++
# ---------------------------------------------------------------------------
# CMake expects a single executable for CMAKE_C_COMPILER / CMAKE_CXX_COMPILER.
# Zig uses `zig cc` (two args), so we create tiny wrapper scripts.

set(_zig_wrapper_dir "${CMAKE_CURRENT_BINARY_DIR}/_zig_wrappers")
file(MAKE_DIRECTORY "${_zig_wrapper_dir}")

# C compiler wrapper
file(WRITE "${_zig_wrapper_dir}/zig-cc"
    "#!/bin/sh\nexec \"${_zig_bin}\" cc -target x86_64-linux-musl \"$@\"\n")
file(CHMOD "${_zig_wrapper_dir}/zig-cc"
    PERMISSIONS OWNER_READ OWNER_WRITE OWNER_EXECUTE
                GROUP_READ GROUP_EXECUTE
                WORLD_READ WORLD_EXECUTE)

# C++ compiler wrapper
file(WRITE "${_zig_wrapper_dir}/zig-c++"
    "#!/bin/sh\nexec \"${_zig_bin}\" c++ -target x86_64-linux-musl \"$@\"\n")
file(CHMOD "${_zig_wrapper_dir}/zig-c++"
    PERMISSIONS OWNER_READ OWNER_WRITE OWNER_EXECUTE
                GROUP_READ GROUP_EXECUTE
                WORLD_READ WORLD_EXECUTE)

set(CMAKE_C_COMPILER   "${_zig_wrapper_dir}/zig-cc")
set(CMAKE_CXX_COMPILER "${_zig_wrapper_dir}/zig-c++")

message(STATUS "[Toolchain/zig-musl] Using zig cc -target x86_64-linux-musl")

unset(_zig_bin)

# ---------------------------------------------------------------------------
# Force fully static linking
# ---------------------------------------------------------------------------
set(CMAKE_EXE_LINKER_FLAGS_INIT "-static")
set(CMAKE_FIND_LIBRARY_SUFFIXES ".a")
set(BUILD_SHARED_LIBS OFF CACHE BOOL "musl toolchain forces static linking" FORCE)

# Optional: static-PIE for ASLR protection on static binaries
option(MUSL_STATIC_PIE "Build static-PIE binaries (requires musl 1.2+)" OFF)
if(MUSL_STATIC_PIE)
    set(CMAKE_EXE_LINKER_FLAGS_INIT "-static-pie")
    message(STATUS "[Toolchain/zig-musl] Static-PIE enabled")
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

message(STATUS "[Toolchain] x86_64 Linux musl via Zig (fully static)")

# ---------------------------------------------------------------------------
# Search policy — prefer static libraries only
# ---------------------------------------------------------------------------
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)

# ---------------------------------------------------------------------------
# Disable sanitizers — they are not compatible with musl
# ---------------------------------------------------------------------------
set(ENABLE_ASAN  OFF CACHE BOOL "ASan not supported with musl" FORCE)
set(ENABLE_TSAN  OFF CACHE BOOL "TSan not supported with musl" FORCE)
set(ENABLE_UBSAN OFF CACHE BOOL "UBSan not supported with musl" FORCE)
set(ENABLE_MSAN  OFF CACHE BOOL "MSan not supported with musl" FORCE)

message(STATUS "[Toolchain] x86_64 Linux musl via Zig (fully static)")
