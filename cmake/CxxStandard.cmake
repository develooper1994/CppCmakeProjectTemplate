# cmake/CxxStandard.cmake
# Automatic C++ standard detection and CUDA-version-aware standard selection.
#
# ┌─────────────────────────────────────────────────────────────────┐
# │  Public API                                                     │
# ├────────────────────────────┬────────────────────────────────────┤
# │  detect_cxx_standard()     │ Three-strategy pipeline; sets      │
# │    [MIN <std>]             │ CMAKE_CXX_STANDARD to the highest  │
# │    [MAX <std>]             │ std in [MIN..MAX] that the         │
# │    [QUIET]                 │ compiler + stdlib both support.    │
# │                            │ No-op if user set value via CLI /  │
# │                            │ preset / cache.                    │
# ├────────────────────────────┬────────────────────────────────────┤
# │  cuda_compatible_cxx_standard(                                  │
# │    <cuda_version>          │ Sets <out_var> to the maximum      │
# │    <out_var>)              │ C++ standard supported as device   │
# │                            │ code by the given CUDA toolkit     │
# │                            │ version string (e.g. "12.0").      │
# └────────────────────────────┴────────────────────────────────────┘
#
# Detection strategy pipeline (highest priority → lowest):
#
#   Strategy A — CMake feature-list probe (fast, no compilation)
#       Checks CMAKE_CXX_COMPILE_FEATURES for "cxx_std_XX".
#       Used as a fast diagnostic; NOT a hard gate.
#
#   Strategy B — Direct compile probe  (_cxx_compile_probe)
#       Compiles a small canary source with -std=c++XX.
#       Authoritative: validates both language support AND stdlib
#       header availability.  Catches cross-toolchains where CMake
#       under-populates the feature list.
#
#   Strategy C — Compiler-version heuristic  (_compiler_version_max_std)
#       Pure lookup table: compiler ID + version → max expected std.
#       Applied only when Strategy B fails for every candidate.
#       Emits a CMake WARNING — treat as best-effort only.
#
# Supported standard range: 98 (C++98/C++03) · 11 · 14 · 17 · 20 · 23
#   Note: C++03 is treated as C++98 — they share CMake standard value '98'
#         and the same -std=c++98 compiler flag.
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
include(CheckCXXSourceCompiles)

# ---------------------------------------------------------------------------
# _cxx_compile_probe(<std_int> <out_var>)
#
# Strategy B of the detection pipeline.  Compiles a canary source with an
# explicit -std=c++XX flag (or MSVC-native feature-list proxy) to verify
# that both the compiler syntax AND the standard-library headers for that
# standard are available.  This catches:
#   • compilers that advertise a feature in CMAKE_CXX_COMPILE_FEATURES but
#     ship an incomplete stdlib (e.g. bare cross-toolchains),
#   • old CMake versions that under-populate the compile-feature list,
#   • C++98/11/14 detection (CMake feature list is often sparse for these).
#
# Note: C++03 is treated as C++98 — they share CMake standard value '98'
#       and the same -std=c++98 compiler flag.
#
# Results are cached as CXX_COMPILE_PROBE_<std>_OK (INTERNAL) so each std
# is probed only once per CMake configure tree.
#
# Canary sources (test language features AND stdlib headers):
#   C++98/03 — templates + STL containers (baseline)
#   C++11    — nullptr, range-for, lambda, noexcept (language only)
#   C++14    — generic lambda + std::integer_sequence (C++14 lib feature)
#   C++17    — std::optional + std::variant
#   C++20    — std::concepts + std::ranges::views::iota
#   C++23    — std::expected
# ---------------------------------------------------------------------------
function(_cxx_compile_probe std out_var)
    # Return cached result if already probed in this build tree.
    if(DEFINED CACHE{CXX_COMPILE_PROBE_${std}_OK})
        set(${out_var} "${CXX_COMPILE_PROBE_${std}_OK}" PARENT_SCOPE)
        return()
    endif()

    # MSVC uses /std:c++XX set automatically by CMake — manual -std= flags
    # are rejected.  CMake's feature list is reliable for MSVC, so derive
    # the result directly from it (no compilation needed).
    if(MSVC)
        if("cxx_std_${std}" IN_LIST CMAKE_CXX_COMPILE_FEATURES)
            set(CXX_COMPILE_PROBE_${std}_OK TRUE CACHE INTERNAL
                "C++${std} compile probe (MSVC feature-list proxy)")
        else()
            set(CXX_COMPILE_PROBE_${std}_OK FALSE CACHE INTERNAL
                "C++${std} compile probe (MSVC feature-list proxy)")
        endif()
        set(${out_var} "${CXX_COMPILE_PROBE_${std}_OK}" PARENT_SCOPE)
        return()
    endif()

    # GCC / Clang / ICC — choose the right -std= flag.
    if(std EQUAL 98)
        set(_flag "-std=c++98")   # also covers C++03
    else()
        set(_flag "-std=c++${std}")
    endif()

    # Canary sources — each tests language features AND stdlib presence.
    if(std EQUAL 23)
        set(_src [[
#include <expected>
int main() { std::expected<int,int> e{42}; return e.value(); }
]])
    elseif(std EQUAL 20)
        set(_src [[
#include <concepts>
#include <ranges>
int main() { auto v = std::views::iota(0, 4); (void)v; return 0; }
]])
    elseif(std EQUAL 17)
        set(_src [[
#include <optional>
#include <variant>
int main() {
    std::optional<int> x{1};
    std::variant<int, double> y{2};
    return x.value() + std::get<int>(y) == 3 ? 0 : 1;
}
]])
    elseif(std EQUAL 14)
        set(_src [[
#include <utility>
int main() {
    // generic lambda: C++14 language feature
    auto fn = [](auto x) { return x * 2; };
    // std::integer_sequence: C++14 library feature
    using seq_t = std::integer_sequence<int, 1, 2, 3>;
    (void)seq_t{};
    return fn(21) == 42 ? 0 : 1;
}
]])
    elseif(std EQUAL 11)
        set(_src [[
#include <utility>
int main() {
    // nullptr, range-for, lambda, noexcept — C++11 language features only
    int* p = nullptr;
    int arr[] = {1, 2, 3};
    auto lam = [&]() noexcept -> int {
        int s = 0;
        for (auto x : arr) s += x;
        return s;
    };
    return (p == nullptr && lam() == 6) ? 0 : 1;
}
]])
    else()  # C++98 / C++03
        set(_src [[
#include <iostream>
#include <vector>
template<typename T> T identity(T v) { return v; }
int main() {
    std::vector<int> v;
    v.push_back(identity(42));
    return v.back() == 42 ? 0 : 1;
}
]])
    endif()

    set(_saved_flags "${CMAKE_REQUIRED_FLAGS}")
    set(CMAKE_REQUIRED_FLAGS "${_flag}")
    check_cxx_source_compiles("${_src}" CXX_COMPILE_PROBE_${std}_OK)
    set(CMAKE_REQUIRED_FLAGS "${_saved_flags}")

    set(${out_var} "${CXX_COMPILE_PROBE_${std}_OK}" PARENT_SCOPE)
endfunction()

# ---------------------------------------------------------------------------
# _compiler_version_max_std(<out_var>)
#
# Strategy C (heuristic / last resort).  Returns the maximum C++ standard
# the active compiler is expected to support, based only on its ID and
# version number.  This is LESS reliable than compile probes — use only
# when Strategy B has failed for every candidate in [MIN..MAX].
#
# Conservative tables (full stable support, not just partial):
#   GCC    ≥13→23  ≥11→20  ≥7→17  ≥5→14  ≥4.8→11  else→98
#   Clang  ≥17→23  ≥10→20  ≥5→17  ≥3.4→14  ≥3.3→11  else→98
#   MSVC   ≥1930→23  ≥1929→20  ≥1914→17  ≥1900→14  ≥1600→11  else→98
#   Intel/IntelLLVM  ≥2021→20  ≥19→17  ≥17→14  else→11
#   (unknown compiler) → 98
# ---------------------------------------------------------------------------
function(_compiler_version_max_std out_var)
    set(_max 98)   # absolute safe fallback

    if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
        if    (CMAKE_CXX_COMPILER_VERSION VERSION_GREATER_EQUAL "13.0")
            set(_max 23)
        elseif(CMAKE_CXX_COMPILER_VERSION VERSION_GREATER_EQUAL "11.0")
            set(_max 20)
        elseif(CMAKE_CXX_COMPILER_VERSION VERSION_GREATER_EQUAL "7.0")
            set(_max 17)
        elseif(CMAKE_CXX_COMPILER_VERSION VERSION_GREATER_EQUAL "5.0")
            set(_max 14)
        elseif(CMAKE_CXX_COMPILER_VERSION VERSION_GREATER_EQUAL "4.8")
            set(_max 11)
        endif()

    elseif(CMAKE_CXX_COMPILER_ID MATCHES "Clang")
        if    (CMAKE_CXX_COMPILER_VERSION VERSION_GREATER_EQUAL "17.0")
            set(_max 23)
        elseif(CMAKE_CXX_COMPILER_VERSION VERSION_GREATER_EQUAL "10.0")
            set(_max 20)
        elseif(CMAKE_CXX_COMPILER_VERSION VERSION_GREATER_EQUAL "5.0")
            set(_max 17)
        elseif(CMAKE_CXX_COMPILER_VERSION VERSION_GREATER_EQUAL "3.4")
            set(_max 14)
        elseif(CMAKE_CXX_COMPILER_VERSION VERSION_GREATER_EQUAL "3.3")
            set(_max 11)
        endif()

    elseif(CMAKE_CXX_COMPILER_ID STREQUAL "MSVC")
        if    (MSVC_VERSION GREATER_EQUAL 1930)   # VS 2022
            set(_max 23)
        elseif(MSVC_VERSION GREATER_EQUAL 1929)   # VS 2019 16.11+
            set(_max 20)
        elseif(MSVC_VERSION GREATER_EQUAL 1914)   # VS 2017 15.7+
            set(_max 17)
        elseif(MSVC_VERSION GREATER_EQUAL 1900)   # VS 2015
            set(_max 14)
        elseif(MSVC_VERSION GREATER_EQUAL 1600)   # VS 2010
            set(_max 11)
        endif()

    elseif(CMAKE_CXX_COMPILER_ID MATCHES "Intel|IntelLLVM")
        if    (CMAKE_CXX_COMPILER_VERSION VERSION_GREATER_EQUAL "2021.1")
            set(_max 20)
        elseif(CMAKE_CXX_COMPILER_VERSION VERSION_GREATER_EQUAL "19.0")
            set(_max 17)
        elseif(CMAKE_CXX_COMPILER_VERSION VERSION_GREATER_EQUAL "17.0")
            set(_max 14)
        else()
            set(_max 11)
        endif()
    endif()

    set(${out_var} ${_max} PARENT_SCOPE)
endfunction()

# ---------------------------------------------------------------------------
# detect_cxx_standard([MIN <std>] [MAX <std>] [QUIET])
#
# Three-strategy pipeline to find the highest C++ standard that the active
# compiler AND its standard library both support, within [MIN..MAX]:
#
#   Strategy A — CMake feature-list check (fast, no compilation)
#       Checks CMAKE_CXX_COMPILE_FEATURES for "cxx_std_XX".
#       Diagnostic only; NOT used as a hard gate.
#
#   Strategy B — direct compile probe  (see _cxx_compile_probe)
#       Compiles a canary source with -std=c++XX.  Always attempted
#       regardless of Strategy A result, so cross-toolchains where CMake
#       under-populates the feature list are handled correctly.
#       This is the authoritative gate: a standard is accepted only if
#       the canary compiles successfully.
#
#   Strategy C — compiler-version heuristic  (see _compiler_version_max_std)
#       Pure lookup table, no compilation.  Applied only when Strategy B
#       failed for every candidate in [MIN..MAX].  Emits a WARNING.
#
# Supported range: 98 (C++98/C++03) · 11 · 14 · 17 · 20 · 23
#   Note: C++03 → pass MIN 98.  CMake has no separate "03" constant.
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
        set(_min_std 17)   # project-wide minimum (override with MIN 11 / MIN 98)
    endif()
    if(NOT _max_std)
        set(_max_std 23)   # highest standard we currently probe
    endif()

    # Candidates probed highest-to-lowest; includes legacy standards.
    # C++03 is represented by 98 (same CMake value and -std= flag).
    set(_candidates 23 20 17 14 11 98)
    set(_selected "")   # empty = nothing accepted yet

    foreach(_std IN LISTS _candidates)
        if(_std GREATER _max_std)
            continue()
        endif()
        if(_std LESS _min_std)
            break()   # descending list — nothing below MIN can win
        endif()

        # Strategy A: fast feature-list check (diagnostic; not a hard gate)
        set(_feature_ok FALSE)
        if("cxx_std_${_std}" IN_LIST CMAKE_CXX_COMPILE_FEATURES)
            set(_feature_ok TRUE)
        endif()

        # Strategy B: compile probe — authoritative result
        _cxx_compile_probe(${_std} _compile_ok)

        if(_compile_ok)
            if(NOT _DCS_QUIET)
                if(NOT _feature_ok)
                    message(STATUS
                        "[CxxStd] C++${_std}: compile probe OK "
                        "(CMake feature list absent — cross-toolchain?)")
                else()
                    message(STATUS "[CxxStd] C++${_std}: OK")
                endif()
            endif()
            set(_selected ${_std})
            break()
        else()
            if(NOT _DCS_QUIET)
                if(_feature_ok)
                    message(STATUS
                        "[CxxStd] C++${_std}: feature list OK but compile FAIL "
                        "(stdlib incomplete?)")
                else()
                    message(STATUS "[CxxStd] C++${_std}: not supported (skipping)")
                endif()
            endif()
        endif()
    endforeach()

    # Strategy C: heuristic fallback — only when all compile probes failed
    if(NOT _selected)
        _compiler_version_max_std(_h_max)
        # Clamp to [min_std, max_std]
        if(_h_max GREATER _max_std)
            set(_h_max ${_max_std})
        endif()
        if(_h_max LESS _min_std)
            set(_h_max ${_min_std})
        endif()
        set(_selected ${_h_max})
        if(NOT _DCS_QUIET)
            message(WARNING
                "[CxxStd] All compile probes failed for "
                "[C++${_min_std}..C++${_max_std}]. "
                "Falling back to compiler-version heuristic: C++${_selected}. "
                "Build may fail — set CMAKE_CXX_STANDARD explicitly if needed.")
        endif()
    endif()

    # Always expose detected value for callers (non-cache — re-evaluated each run)
    set(CXX_STANDARD_DETECTED ${_selected} PARENT_SCOPE)

    # Only write cache if the user hasn't already set a preference.
    # DEFINED CACHE{VAR} checks the cache specifically (CMake ≥ 3.14).
    if(NOT DEFINED CACHE{CMAKE_CXX_STANDARD})
        set(CMAKE_CXX_STANDARD "${_selected}" CACHE STRING
            "C++ standard (auto-detected: C++${_selected}; override with -DCMAKE_CXX_STANDARD=XX)")
        set_property(CACHE CMAKE_CXX_STANDARD PROPERTY STRINGS 98 11 14 17 20 23)
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
