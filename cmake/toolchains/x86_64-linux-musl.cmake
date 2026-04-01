# cmake/toolchains/x86_64-linux-musl.cmake
# Fully static Linux builds using musl libc.
#
# Produces position-independent, statically linked binaries with no glibc
# dependency — ideal for single-binary deployment, containers, and
# reproducible builds.
#
# Requirements (pick one):
#
#   Option A — musl-tools (C only, lightweight):
#     sudo apt install musl-tools
#     Provides musl-gcc wrapper.  C++ support is limited because the host
#     libstdc++ is linked against glibc.
#
#   Option B — Alpine Docker (C + C++, recommended):
#     docker run --rm -v $PWD:/workspace -w /workspace alpine:3.21 \
#       sh -c "apk add gcc g++ cmake ninja musl-dev linux-headers git python3 && \
#              cmake --preset gcc-release-static-x86_64-linux-musl && \
#              cmake --build --preset gcc-release-static-x86_64-linux-musl"
#     Native musl g++ — full C++ support out of the box.
#
#   Option C — musl-cross-make (C + C++, standalone):
#     Build a complete x86_64-linux-musl cross-toolchain from source.
#     See: https://github.com/richfelker/musl-cross-make
#
# Usage:
#   cmake --preset gcc-release-static-x86_64-linux-musl
#   # or manually:
#   cmake -DCMAKE_TOOLCHAIN_FILE=cmake/toolchains/x86_64-linux-musl.cmake \
#         -B build/musl -S .
#
# Notes:
#   - Sanitizers (ASan, TSan, UBSan, MSan) are NOT compatible with musl.
#   - Dynamic linking is not supported with this toolchain (BUILD_SHARED_LIBS forced OFF).
#   - For ASLR protection on static binaries, pass -DMUSL_STATIC_PIE=ON.

set(CMAKE_SYSTEM_NAME    Linux)
set(CMAKE_SYSTEM_PROCESSOR x86_64)

# ---------------------------------------------------------------------------
# Compiler selection
# ---------------------------------------------------------------------------
# Prefer musl-cross-make full toolchain if available, otherwise fall back
# to the musl-gcc wrapper from musl-tools.

find_program(_musl_cross_gcc  x86_64-linux-musl-gcc)
find_program(_musl_cross_gxx  x86_64-linux-musl-g++)
find_program(_musl_gcc_wrapper musl-gcc)

if(_musl_cross_gcc AND _musl_cross_gxx)
    # Full musl cross-toolchain (musl-cross-make or Alpine native)
    set(CMAKE_C_COMPILER   x86_64-linux-musl-gcc)
    set(CMAKE_CXX_COMPILER x86_64-linux-musl-g++)
    message(STATUS "[Toolchain/musl] Using musl cross-toolchain")
elseif(_musl_gcc_wrapper)
    # musl-tools wrapper — C works, C++ uses host g++ with static linking
    set(CMAKE_C_COMPILER   musl-gcc)
    set(CMAKE_CXX_COMPILER g++)
    message(STATUS "[Toolchain/musl] Using musl-gcc wrapper (C++ via host g++ -static)")
    message(WARNING
        "musl-gcc wrapper provides C-only musl support. "
        "C++ links libstdc++ statically from the host toolchain. "
        "For full musl C++ support, use Alpine Docker or musl-cross-make.")
else()
    message(FATAL_ERROR
        "No musl toolchain found.\n"
        "Install one of:\n"
        "  (a) sudo apt install musl-tools          (C only, quick)\n"
        "  (b) Alpine Docker image                   (C+C++, recommended)\n"
        "  (c) musl-cross-make                       (C+C++, standalone)\n")
endif()

unset(_musl_cross_gcc)
unset(_musl_cross_gxx)
unset(_musl_gcc_wrapper)

# ---------------------------------------------------------------------------
# Force fully static linking
# ---------------------------------------------------------------------------
set(CMAKE_EXE_LINKER_FLAGS_INIT "-static")
set(CMAKE_FIND_LIBRARY_SUFFIXES ".a")
set(BUILD_SHARED_LIBS OFF CACHE BOOL "musl toolchain forces static linking" FORCE)

# Optional: static-PIE for ASLR protection on static binaries (musl 1.2+)
option(MUSL_STATIC_PIE "Build static-PIE binaries (requires musl 1.2+)" OFF)
if(MUSL_STATIC_PIE)
    set(CMAKE_EXE_LINKER_FLAGS_INIT "-static-pie")
    message(STATUS "[Toolchain/musl] Static-PIE enabled (ASLR on static binaries)")
endif()

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

message(STATUS "[Toolchain] x86_64 Linux musl (fully static)")
