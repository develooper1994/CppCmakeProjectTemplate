# cmake/CxxStandard.cmake
# Automatic C++ standard detection and CUDA-version-aware standard selection.
#
# ┌─────────────────────────────────────────────────────────────┐
# │  Public API                                                 │
# ├──────────────────────────┬──────────────────────────────────┤
# │  detect_cxx_standard()   │ Probe compiler features and set  │
# │    [MIN <std>]           │ CMAKE_CXX_STANDARD to the        │
# │    [MAX <std>]           │ highest supported std in [MIN,   │
# │    [QUIET]               │ MAX]. No-op if already set by    │
# │                          │ user (CLI / preset / cache).     │
# ├──────────────────────────┬──────────────────────────────────┤
# │  cuda_compatible_cxx_standard(                              │
# │    <cuda_version>        │ Sets <out_var> to the maximum    │
# │    <out_var>)            │ C++ standard supported as device │
# │                          │ code by the given CUDA toolkit   │
# │                          │ version string (e.g. "12.0").    │
# └──────────────────────────┴──────────────────────────────────┘
#
# Auto-detection is triggered at include() time via detect_cxx_standard().
# cuda_compatible_cxx_standard() is called lazily by cmake/CUDA.cmake.
#
# Override (always wins, even over detected value):
#   cmake -DCMAKE_CXX_STANDARD=20 ...
#   or set it in a CMakePresets.json cacheVariable.
#
# CUDA device-code C++ standard compatibility table
# ─────────────────────────────────────────────────
#   CUDA < 9.0          → device code: max C++11
#   CUDA 9.0 – 10.x     → device code: max C++14
#   CUDA 11.0 – 12.1    → device code: max C++17
#   CUDA ≥ 12.2         → device code: max C++20
#
#   Host code can always use a higher standard than device code.
#   A CMake warning is emitted when host > device limit.
#
# Reference:
#   CUDA C++ Programming Guide: "C++ Language Support"
#   https://docs.nvidia.com/cuda/cuda-c-programming-guide/index.html#c-cplusplus-language-support

cmake_minimum_required(VERSION 3.25)  # require for DEFINED CACHE{} syntax

# ---------------------------------------------------------------------------
# detect_cxx_standard([MIN <std>] [MAX <std>] [QUIET])
#
# Probes CMAKE_CXX_COMPILE_FEATURES to find the highest std the active
# compiler supports, bounded by [MIN..MAX].
#
# Side effects:
#   Sets CMAKE_CXX_STANDARD in the cache (if not already set by user).
#   Sets CXX_STANDARD_DETECTED (non-cache) to the detected std integer.
# ---------------------------------------------------------------------------
function(detect_cxx_standard)
    cmake_parse_arguments(_DCS "QUIET" "MIN;MAX" "" ${ARGN})

    # Defaults for bounds
    set(_min_std "${_DCS_MIN}")
    set(_max_std "${_DCS_MAX}")
    if(NOT _min_std)
        set(_min_std 17)   # minimum we care about
    endif()
    if(NOT _max_std)
        set(_max_std 23)   # highest we try to detect
    endif()

    # Probe from highest to lowest within [min..max]
    set(_candidates 23 20 17 14 11)
    set(_selected "${_min_std}")   # safe fallback = minimum

    foreach(_std IN LISTS _candidates)
        if(_std GREATER _max_std)
            continue()
        endif()
        if(_std LESS _min_std)
            break()   # list is descending — no point continuing
        endif()
        if("cxx_std_${_std}" IN_LIST CMAKE_CXX_COMPILE_FEATURES)
            set(_selected ${_std})
            break()
        endif()
    endforeach()

    # Always expose detected value for callers (non-cache — re-evaluated each run)
    set(CXX_STANDARD_DETECTED ${_selected} PARENT_SCOPE)

    # Only write cache if the user hasn't already set a preference.
    # DEFINED CACHE{VAR} checks the cache specifically (CMake ≥ 3.14).
    if(NOT DEFINED CACHE{CMAKE_CXX_STANDARD})
        set(CMAKE_CXX_STANDARD "${_selected}" CACHE STRING
            "C++ standard (auto-detected: C++${_selected}; override with -DCMAKE_CXX_STANDARD=XX)")
        set_property(CACHE CMAKE_CXX_STANDARD PROPERTY STRINGS 11 14 17 20 23)
        if(NOT _DCS_QUIET)
            message(STATUS "[CxxStd] Auto-detected C++ standard: C++${_selected}")
        endif()
    else()
        if(NOT _DCS_QUIET)
            message(STATUS
                "[CxxStd] C++ standard: C++${CMAKE_CXX_STANDARD} "
                "(explicit — override active; auto-detected would be C++${_selected})")
        endif()
    endif()
endfunction()

# ---------------------------------------------------------------------------
# cuda_compatible_cxx_standard(<cuda_version_string> <out_var>)
#
# Returns the maximum C++ standard usable as CUDA *device* code for the
# given toolkit version.  Host code is unaffected and can use a higher std.
#
# Example:
#   cuda_compatible_cxx_standard("${CUDAToolkit_VERSION}" _max)
#   # _max = 17 for CUDA 12.0
# ---------------------------------------------------------------------------
function(cuda_compatible_cxx_standard cuda_version out_var)
    if(cuda_version VERSION_LESS "9.0")
        # CUDA 7.x / 8.x: only partial C++11 device support
        set(_max 11)
    elseif(cuda_version VERSION_LESS "11.0")
        # CUDA 9.x / 10.x: full C++14 device code
        set(_max 14)
    elseif(cuda_version VERSION_LESS "12.2")
        # CUDA 11.0 – 12.1: full C++17 device code
        set(_max 17)
    else()
        # CUDA ≥ 12.2: C++20 device code (experimental in 12.0–12.1, full in 12.2+)
        set(_max 20)
    endif()
    set(${out_var} ${_max} PARENT_SCOPE)
endfunction()

# ---------------------------------------------------------------------------
# Module-level: auto-run detect_cxx_standard() at include() time.
# Any subsequent include() of this file is a no-op (CMake include guard).
# ---------------------------------------------------------------------------
detect_cxx_standard()
