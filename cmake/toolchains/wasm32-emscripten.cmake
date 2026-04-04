# cmake/toolchains/wasm32-emscripten.cmake
# WebAssembly builds via Emscripten (emcc/em++).
#
# Produces .wasm + .js glue or standalone .wasm modules suitable for
# browser, Node.js, or WASI runtimes.
#
# Requirements:
#   Install Emscripten SDK:
#     git clone https://github.com/emscripten-core/emsdk.git
#     cd emsdk && ./emsdk install latest && ./emsdk activate latest
#     source emsdk_env.sh
#
# Usage:
#   cmake --preset gcc-release-static-wasm32-emscripten
#   cmake --build --preset gcc-release-static-wasm32-emscripten
#
# Notes:
#   - Emscripten provides its own toolchain file via $EMSDK/upstream/emscripten/cmake/Modules/Platform/Emscripten.cmake
#   - This file delegates to it after setting project-specific defaults.
#   - Static linkage is the only meaningful option for WASM.

# --- Locate Emscripten toolchain ---
if(DEFINED ENV{EMSDK})
    set(_EMSDK "$ENV{EMSDK}")
else()
    message(FATAL_ERROR
        "EMSDK environment variable not set.\n"
        "Install Emscripten: https://emscripten.org/docs/getting_started/downloads.html\n"
        "Then run: source <emsdk>/emsdk_env.sh")
endif()

set(_EM_TOOLCHAIN "${_EMSDK}/upstream/emscripten/cmake/Modules/Platform/Emscripten.cmake")
if(NOT EXISTS "${_EM_TOOLCHAIN}")
    message(FATAL_ERROR "Emscripten CMake toolchain not found at: ${_EM_TOOLCHAIN}")
endif()

include("${_EM_TOOLCHAIN}")

# --- Project defaults ---
set(CMAKE_SYSTEM_NAME Emscripten)
set(CMAKE_SYSTEM_PROCESSOR wasm32)

# Force static linkage (shared libraries are not meaningful in WASM)
set(BUILD_SHARED_LIBS OFF CACHE BOOL "WASM targets are always static" FORCE)

# Optimisation flags for release builds
set(CMAKE_C_FLAGS_RELEASE   "-O2 -DNDEBUG" CACHE STRING "" FORCE)
set(CMAKE_CXX_FLAGS_RELEASE "-O2 -DNDEBUG" CACHE STRING "" FORCE)

# Enable pthreads support (optional — uncomment if needed)
# set(CMAKE_C_FLAGS   "${CMAKE_C_FLAGS}   -pthread" CACHE STRING "" FORCE)
# set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -pthread" CACHE STRING "" FORCE)
# set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} -pthread -sPTHREAD_POOL_SIZE=4" CACHE STRING "" FORCE)
