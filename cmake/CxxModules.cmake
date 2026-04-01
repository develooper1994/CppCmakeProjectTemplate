# cmake/CxxModules.cmake
#
# C++20 module-unit support using CMake 3.28+ native module scanning.
#
# Usage:
#   include(CxxModules)
#   enable_cxx_modules(<target>)
#
# The target must have its module sources added via FILE_SET CXX_MODULES:
#   target_sources(<target>
#       PUBLIC FILE_SET CXX_MODULES FILES src/<name>.cppm)
#
# Guard: no-op (with a WARNING) when the target's CXX_STANDARD < 20.

if(CMAKE_VERSION VERSION_LESS "3.28")
    message(WARNING "[CxxModules] CMake >= 3.28 is required for native C++20 module scanning. "
                    "Upgrade CMake or disable ENABLE_CXX_MODULES.")
    # Define a stub so callers don't hit an "unknown function" error.
    function(enable_cxx_modules target)
        message(WARNING "[CxxModules] enable_cxx_modules(${target}) skipped: CMake < 3.28")
    endfunction()
    return()
endif()

function(enable_cxx_modules target)
    # Resolve the effective C++ standard for this target.
    get_target_property(_std "${target}" CXX_STANDARD)
    if(NOT _std OR _std STREQUAL "${target}-NOTFOUND")
        set(_std "${CMAKE_CXX_STANDARD}")
    endif()

    # Guard: C++20 modules require at least C++20.
    if(NOT _std OR _std LESS 20)
        message(WARNING
            "[CxxModules] enable_cxx_modules(${target}): C++20 modules require "
            "CXX_STANDARD >= 20 (current: '${_std}'). Skipping.")
        return()
    endif()

    # Enable CMake 3.28+ per-target module-unit scanning.
    set_target_properties("${target}" PROPERTIES CXX_SCAN_FOR_MODULES ON)

    # Compiler-specific flags.
    if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
        # GCC 13: experimental module support via -fmodules-ts.
        # GCC 14+ has improved (but still evolving) support.
        target_compile_options("${target}" PRIVATE -fmodules-ts)
        message(STATUS "[CxxModules] ${target}: GCC modules enabled (-fmodules-ts, experimental)")
    elseif(CMAKE_CXX_COMPILER_ID MATCHES "Clang")
        # Clang 16+ has native C++20 module support; no extra flags required.
        message(STATUS "[CxxModules] ${target}: Clang native C++20 modules enabled")
    elseif(CMAKE_CXX_COMPILER_ID STREQUAL "MSVC")
        # MSVC 19.28+ supports modules via /experimental:module (older) or natively (VS 2022+).
        # Modern MSVC (≥19.34) enables modules by default in C++20 mode.
        message(STATUS "[CxxModules] ${target}: MSVC C++20 modules enabled")
    else()
        message(WARNING "[CxxModules] ${target}: Unknown compiler '${CMAKE_CXX_COMPILER_ID}' — "
                        "C++20 module support is untested.")
    endif()
endfunction()
