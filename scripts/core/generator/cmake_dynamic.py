"""
core/generator/cmake_dynamic.py — Dynamic cmake module generators.

These modules are generated from tool.toml context using Python f-strings.
Unlike STATIC modules (verbatim embedded), DYNAMIC modules change based on
project configuration (enabled features, library list, app list, etc.).

Components:
  - ProjectConfigs.cmake  — ENABLE_* options driven by [cmake_modules]
  - FeatureFlags.cmake    — PROJECT_ALL_OPTIONS list matching ProjectConfigs
"""
from __future__ import annotations

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path
    from core.generator.engine import ProjectContext


def generate_project_configs(ctx: ProjectContext) -> str:
    """Generate cmake/ProjectConfigs.cmake from tool.toml context."""
    enabled = set(ctx.cmake_modules.get("enabled", []))

    # Determine which option blocks to include based on enabled modules
    sections: list[str] = []

    # Header
    sections.append(
        "# cmake/ProjectConfigs.cmake\n"
        "# Centralized configuration for all project-wide CMake defaults\n"
    )

    # --- Build Options (always present) ---
    sections.append(
        "# --- Build Options ---\n"
        'option(BUILD_SHARED_LIBS    "Build libraries as shared"          OFF)\n'
        'option(ENABLE_UNITY_BUILD   "Enable unity builds"                OFF)\n'
        'option(ENABLE_WERROR        "Treat warnings as errors"           OFF)\n'
        'option(ENABLE_UNIT_TESTS    "Build unit tests"                   ON)\n'
        'option(ENABLE_DOCS          "Build documentation"                OFF)\n'
        'option(ENABLE_COVERAGE      "Enable code coverage reporting"     OFF)\n'
    )

    # --- Quality & Security Options ---
    quality_opts: list[str] = []
    if "Sanitizers" in enabled:
        quality_opts.extend([
            'option(ENABLE_ASAN          "Enable Address Sanitizer"           OFF)',
            'option(ENABLE_UBSAN         "Enable Undefined Behavior Sanitizer" OFF)',
            'option(ENABLE_TSAN          "Enable Thread Sanitizer"            OFF)',
        ])
    if "Hardening" in enabled:
        quality_opts.append('option(ENABLE_HARDENING     "Enable security hardening flags"    OFF)')
    if "StaticAnalyzers" in enabled or "IWYU" in enabled:
        quality_opts.append('option(ENABLE_CLANG_TIDY    "Enable Clang-Tidy static analysis"  OFF)')
        quality_opts.append('option(ENABLE_CPPCHECK      "Enable Cppcheck static analysis"    OFF)')
    if "Fuzzing" in enabled:
        quality_opts.append('option(ENABLE_FUZZING      "Enable fuzz testing targets"        OFF)')
        quality_opts.append('# NOTE: Valgrind support is planned (ENABLE_VALGRIND). Currently not implemented.')
        quality_opts.append('# When enabled it would wrap ctest runs with valgrind --leak-check=full.')
    if quality_opts:
        sections.append("# --- Quality & Security Options ---\n" + "\n".join(quality_opts) + "\n")

    # --- Performance & Optimization Options ---
    perf_opts: list[str] = []
    if "LTO" in enabled:
        perf_opts.append('option(ENABLE_LTO               "Enable Link-Time Optimization"             OFF)')
    if "BuildCache" in enabled:
        perf_opts.append('option(ENABLE_CCACHE            "Enable compiler caching (ccache/sccache)"  ON)')
    if "Benchmark" in enabled:
        perf_opts.append('option(ENABLE_BENCHMARKS        "Build Google Benchmark targets"             OFF)')
    perf_opts.append('option(ENABLE_VEC_REPORT        "Emit vectorization info (-fopt-info-vec / -Rpass)" OFF)')
    if "Allocators" in enabled:
        perf_opts.extend([
            'set(ENABLE_ALLOCATOR "default" CACHE STRING',
            '    "Allocator backend (default|mimalloc|jemalloc|tcmalloc)")',
            'set_property(CACHE ENABLE_ALLOCATOR PROPERTY STRINGS default mimalloc jemalloc tcmalloc)',
            'option(ENABLE_ALLOCATOR_OVERRIDE_ALL',
            '    "Apply selected allocator backend to all executables/benchmarks"',
            '    OFF)',
        ])
    if perf_opts:
        sections.append("# --- Performance & Optimization Options ---\n" + "\n".join(perf_opts) + "\n")

    # --- Parallelization Options ---
    if "OpenMP" in enabled:
        sections.append(
            "# --- Parallelization Options ---\n"
            'option(ENABLE_OPENMP        "Enable OpenMP threading (links libgomp)"         OFF)\n'
            'option(ENABLE_OPENMP_SIMD   "Enable OpenMP SIMD-only (no runtime dep)"         OFF)\n'
            'option(ENABLE_AUTO_PARALLEL "Enable compiler auto-parallelization of loops"    OFF)\n'
        )

    # --- Qt Options ---
    if "Qt" in enabled:
        sections.append(
            "# --- Qt Options ---\n"
            'option(ENABLE_QT            "Enable Qt5/Qt6 support (requires Qt install)"     OFF)\n'
            'option(ENABLE_QML           "Enable Qt QML/Quick (requires ENABLE_QT)"         OFF)\n'
        )

    # --- GPU Options ---
    if "CUDA" in enabled:
        sections.append(
            "# --- CUDA / GPU Options ---\n"
            'option(ENABLE_CUDA          "Enable CUDA language and GPU target support"       OFF)\n'
        )
    if "HIP" in enabled:
        sections.append(
            "# --- AMD HIP / ROCm Options ---\n"
            'option(ENABLE_HIP           "Enable AMD HIP language and GPU target support (requires ROCm)" OFF)\n'
        )
    if "SYCL" in enabled:
        sections.append(
            "# --- SYCL Options ---\n"
            'option(ENABLE_SYCL          "Enable Intel SYCL / DPC++ support"                OFF)\n'
        )
    if "Metal" in enabled:
        sections.append(
            "# --- Metal Options ---\n"
            'option(ENABLE_METAL         "Enable Apple Metal compute support (macOS only)"   OFF)\n'
        )

    # --- PROJECT_ALL_OPTIONS master list ---
    all_options = _build_all_options_list(enabled)
    opts_str = "\n    ".join(all_options)
    sections.append(
        "# --- Master list — drives FeatureFlags.cmake dynamic generation ---\n"
        "# Add new options here; FeatureFlags.h will update automatically on next cmake run.\n"
        "set(PROJECT_ALL_OPTIONS\n"
        f"    {opts_str}\n"
        '    CACHE STRING "All ENABLE_* toggle options (drives FeatureFlags.h generation)" FORCE\n'
        ")\n"
    )

    # --- Vectorization report block ---
    sections.append(
        '# Apply vectorization report flags globally when requested.\n'
        '# Per-target override: target_compile_options(<tgt> PRIVATE ${_VEC_FLAGS})\n'
        'if(ENABLE_VEC_REPORT)\n'
        '    if(CMAKE_CXX_COMPILER_ID MATCHES "Clang")\n'
        '        set(_VEC_FLAGS\n'
        '            -Rpass=loop-vectorize\n'
        '            -Rpass-missed=loop-vectorize\n'
        '            -Rpass-analysis=loop-vectorize)\n'
        '    elseif(CMAKE_CXX_COMPILER_ID STREQUAL "GNU")\n'
        '        set(_VEC_FLAGS -fopt-info-vec-optimized -fopt-info-vec-missed)\n'
        '    else()\n'
        '        set(_VEC_FLAGS "")\n'
        '    endif()\n'
        '    if(_VEC_FLAGS)\n'
        '        add_compile_options(${_VEC_FLAGS})\n'
        '        message(STATUS "[VecReport] Vectorization info enabled: ${_VEC_FLAGS}")\n'
        '    endif()\n'
        'endif()\n'
    )

    # --- Test Framework Options ---
    test_fw = ctx.tests.get("framework", "gtest")
    gtest_default = "ON" if test_fw == "gtest" else "OFF"
    catch2_default = "ON" if test_fw == "catch2" else "OFF"
    boost_test_default = "ON" if test_fw == "boost_test" else "OFF"
    sections.append(
        "# --- Test Framework Options ---\n"
        "# Only one framework should be ON at a time per build.\n"
        f'option(ENABLE_GTEST         "Use GoogleTest as test framework"   {gtest_default})\n'
        f'option(ENABLE_CATCH2        "Use Catch2 as test framework"       {catch2_default})\n'
        f'option(ENABLE_BOOST_TEST    "Use Boost.Test as test framework"   {boost_test_default})\n'
        "# QTest is enabled automatically when ENABLE_QT=ON (no separate option needed)\n"
    )

    # --- Qt & GUI aliases ---
    if "Qt" in enabled:
        sections.append(
            "# --- Qt & GUI Options ---\n"
            "# Note: ENABLE_QT and ENABLE_QML are declared above — these are aliases kept\n"
            "# for backward compatibility with older presets (CMake ignores re-declarations\n"
            "# when the value is already cached).\n"
        )

    # --- Boost ---
    sections.append(
        '# --- Boost Options ---\n'
        'option(ENABLE_BOOST         "Enable Boost libraries"             OFF)\n'
        'set(BOOST_COMPONENTS "" CACHE STRING\n'
        '    "Semicolon-separated Boost components to find (e.g. filesystem;system)")\n'
    )

    # --- Compiler Defaults ---
    cxx_std = ctx.cxx_standard
    sections.append(
        "# --- Compiler Defaults ---\n"
        "# C++ standard is auto-detected by cmake/CxxStandard.cmake (included before this\n"
        "# file in CMakeLists.txt). The detected value is already in the cache as\n"
        "# CMAKE_CXX_STANDARD. We only set a fallback here in case CxxStandard.cmake\n"
        "# was skipped or the user cleared the cache manually.\n"
        "#\n"
        "# Override: -DCMAKE_CXX_STANDARD=20  or set in a CMakePresets.json cacheVariable.\n"
        "# Per-target: set_target_properties(<t> PROPERTIES CXX_STANDARD 20)\n"
        'if(NOT DEFINED CACHE{CMAKE_CXX_STANDARD})\n'
        '    # CxxStandard.cmake was not loaded — apply a safe baseline\n'
        '    message(WARNING\n'
        '        "[CxxStd] cmake/CxxStandard.cmake was not included. "\n'
        f'        "Defaulting to C++{cxx_std}. Include CxxStandard before ProjectConfigs "\n'
        '        "in CMakeLists.txt for full auto-detection.")\n'
        f'    set(CMAKE_CXX_STANDARD {cxx_std} CACHE STRING\n'
        '        "C++ standard (14|17|20|23) — set cmake/CxxStandard.cmake for auto-detect")\n'
        '    set_property(CACHE CMAKE_CXX_STANDARD PROPERTY STRINGS 11 14 17 20 23)\n'
        'endif()\n'
        '\n'
        'set(CMAKE_CXX_STANDARD_REQUIRED ON)\n'
        'set(CMAKE_CXX_EXTENSIONS        OFF)\n'
        'set(CMAKE_EXPORT_COMPILE_COMMANDS ON)\n'
    )

    # --- MSVC Runtime ---
    sections.append(
        "# --- MSVC Runtime Consistency ---\n"
        "# Ensures all targets (including FetchContent deps like GTest) use the same CRT.\n"
        "# /MD  (MultiThreadedDLL)      when BUILD_SHARED_LIBS=ON  or DLL build\n"
        "# /MT  (MultiThreaded)         when BUILD_SHARED_LIBS=OFF (static build)\n"
        "# Without this, mixing /MT and /MD causes linker errors (LNK2038).\n"
        'if(MSVC)\n'
        '    if(BUILD_SHARED_LIBS)\n'
        '        set(CMAKE_MSVC_RUNTIME_LIBRARY\n'
        '            "MultiThreaded$<$<CONFIG:Debug>:Debug>DLL"\n'
        '            CACHE STRING "MSVC runtime library" FORCE)\n'
        '    else()\n'
        '        set(CMAKE_MSVC_RUNTIME_LIBRARY\n'
        '            "MultiThreaded$<$<CONFIG:Debug>:Debug>"\n'
        '            CACHE STRING "MSVC runtime library" FORCE)\n'
        '    endif()\n'
        '    # GTest must follow the same CRT — set before FetchContent_MakeAvailable\n'
        '    set(gtest_force_shared_crt ${BUILD_SHARED_LIBS} CACHE BOOL "" FORCE)\n'
        'endif()\n'
    )

    # --- Boost find ---
    sections.append(
        '# --- Boost (optional) ---\n'
        'if(ENABLE_BOOST)\n'
        '    if(BOOST_COMPONENTS)\n'
        '        find_package(Boost REQUIRED COMPONENTS ${BOOST_COMPONENTS})\n'
        '    else()\n'
        '        find_package(Boost REQUIRED)\n'
        '    endif()\n'
        '    if(Boost_FOUND)\n'
        '        message(STATUS "Found Boost ${Boost_VERSION}")\n'
        '    endif()\n'
        'endif()\n'
    )

    # --- Project Paths ---
    sections.append(
        '# --- Project Paths ---\n'
        'set(PROJECT_GENERATED_DIR "${CMAKE_BINARY_DIR}/generated"\n'
        '    CACHE PATH "Directory for generated files")\n'
        'file(MAKE_DIRECTORY ${PROJECT_GENERATED_DIR})\n'
    )

    return "\n".join(sections)


def _build_all_options_list(enabled: set[str]) -> list[str]:
    """Build the PROJECT_ALL_OPTIONS list based on enabled modules."""
    opts: list[str] = ["# Tests", "UNIT_TESTS GTEST CATCH2 BOOST_TEST"]

    if "Sanitizers" in enabled:
        opts.extend(["# Sanitizers", "ASAN UBSAN TSAN"])

    analysis = []
    if "StaticAnalyzers" in enabled or "IWYU" in enabled:
        analysis.extend(["CLANG_TIDY", "CPPCHECK"])
    if "CodeCoverage" in enabled:
        analysis.append("COVERAGE")
    if analysis:
        opts.extend(["# Analysis / coverage", " ".join(analysis)])

    perf = []
    if "LTO" in enabled:
        perf.append("LTO")
    if "Benchmark" in enabled:
        perf.append("BENCHMARKS")
    perf.append("VEC_REPORT")
    opts.extend(["# Performance", " ".join(perf)])

    if "OpenMP" in enabled:
        opts.extend(["# Parallelization", "OPENMP OPENMP_SIMD AUTO_PARALLEL"])

    frameworks = []
    if "Qt" in enabled:
        frameworks.extend(["QT", "QML"])
    if "CUDA" in enabled:
        frameworks.append("CUDA")
    if "HIP" in enabled:
        frameworks.append("HIP")
    if "SYCL" in enabled:
        frameworks.append("SYCL")
    if "Metal" in enabled:
        frameworks.append("METAL")
    frameworks.append("BOOST")
    opts.extend(["# Frameworks", " ".join(frameworks)])

    opts.extend(["# Misc", "DOCS"])
    return opts


def generate_feature_flags(ctx: ProjectContext) -> str:
    """Generate cmake/FeatureFlags.cmake — unchanged content (logic-heavy CMake).

    FeatureFlags.cmake is functionally STATIC — its CMake logic is self-contained
    and reads PROJECT_ALL_OPTIONS dynamically at configure time. We emit it
    verbatim since its behavior is driven by ProjectConfigs.cmake values.
    """
    return _FEATURE_FLAGS_CONTENT


# ---------------------------------------------------------------------------
# Public API used by the engine
# ---------------------------------------------------------------------------

def generate_all(ctx: ProjectContext, target_dir: "Path") -> dict[str, str]:
    """Generate all dynamic cmake files. Returns {rel_path: content}."""
    return {
        "cmake/ProjectConfigs.cmake": generate_project_configs(ctx),
        "cmake/FeatureFlags.cmake": generate_feature_flags(ctx),
    }


# ---------------------------------------------------------------------------
# FeatureFlags.cmake — verbatim content (logic is dynamic at CMake configure
# time via PROJECT_ALL_OPTIONS iteration — no Python templating needed)
# ---------------------------------------------------------------------------

_FEATURE_FLAGS_CONTENT = """\
# cmake/FeatureFlags.cmake
# Dynamically generates FeatureFlags.h from PROJECT_ALL_OPTIONS list
# (defined in ProjectConfigs.cmake). Adding a new option to that list
# automatically extends the generated header — no template file needed.
#
# Call once from root CMakeLists.txt (after ProjectConfigs):
#   include(FeatureFlags)
#   generate_feature_flags()
#
# Attach to a target:
#   target_add_feature_flags(<target>)
#   # or link project_feature_flags INTERFACE target directly

function(generate_feature_flags)
    set(GENERATED_DIR "${CMAKE_BINARY_DIR}/generated/project")
    file(MAKE_DIRECTORY "${GENERATED_DIR}")

    # ── Resolve values ─────────────────────────────────────────────────────────
    if(BUILD_SHARED_LIBS)
        set(_shared 1)
        set(_lib_type "Shared")
    else()
        set(_shared 0)
        set(_lib_type "Static")
    endif()

    # ── Build #define block ────────────────────────────────────────────────────
    set(_defines "// BUILD_SHARED_LIBS\\n#define PROJECT_SHARED_LIBS ${_shared}\\n#define PROJECT_LIBRARY_TYPE \\"${_lib_type}\\"\\n\\n")

    foreach(_opt IN LISTS PROJECT_ALL_OPTIONS)
        if(ENABLE_${_opt})
            set(_val 1)
        else()
            set(_val 0)
        endif()
        string(APPEND _defines "// ENABLE_${_opt}\\n#define FEATURE_${_opt} ${_val}\\n")
    endforeach()

    if(ENABLE_QT)
        string(APPEND _defines "// ENABLE_QT → QTest\\n#define FEATURE_QTEST 1\\n")
    else()
        string(APPEND _defines "// ENABLE_QT → QTest\\n#define FEATURE_QTEST 0\\n")
    endif()

    # ── Build features[] entries ───────────────────────────────────────────────
    set(_array_entries "    Feature{\\"shared_libs\\", bool(PROJECT_SHARED_LIBS)},\\n")
    foreach(_opt IN LISTS PROJECT_ALL_OPTIONS)
        string(TOLOWER "${_opt}" _opt_lower)
        string(APPEND _array_entries "    Feature{\\"${_opt_lower}\\", bool(FEATURE_${_opt})},\\n")
    endforeach()
    string(APPEND _array_entries "    Feature{\\"qtest\\", bool(FEATURE_QTEST)},\\n")

    # ── Build configuration summary table ──────────────────────────────────────
    set(_rows "")

    set(_btype "${CMAKE_BUILD_TYPE}")
    if(NOT _btype)
        set(_btype "(multi-config)")
    endif()

    list(APPEND _rows "Project|${PROJECT_NAME} v${PROJECT_VERSION}|")
    list(APPEND _rows "CMake|${CMAKE_VERSION}|min 3.25")
    list(APPEND _rows "Build type|${_btype}|")
    list(APPEND _rows "Libraries|${_lib_type}|BUILD_SHARED_LIBS")
    list(APPEND _rows "C++ standard|C++${CMAKE_CXX_STANDARD}|CMAKE_CXX_STANDARD")
    list(APPEND _rows "Compiler|${CMAKE_CXX_COMPILER_ID} ${CMAKE_CXX_COMPILER_VERSION}|")
    list(APPEND _rows "---|---|---")
    list(APPEND _rows "Unit tests|${ENABLE_UNIT_TESTS}|ENABLE_UNIT_TESTS")

    if(ENABLE_UNIT_TESTS)
        if(ENABLE_GTEST)
            list(APPEND _rows "Test framework|GoogleTest|ENABLE_GTEST")
        elseif(ENABLE_CATCH2)
            list(APPEND _rows "Test framework|Catch2|ENABLE_CATCH2")
        elseif(ENABLE_BOOST_TEST)
            list(APPEND _rows "Test framework|Boost.Test|ENABLE_BOOST_TEST")
        elseif(ENABLE_QT)
            list(APPEND _rows "Test framework|QTest|ENABLE_QT")
        else()
            list(APPEND _rows "Test framework|(none)|")
        endif()
    endif()

    list(APPEND _rows "---|---|---")
    list(APPEND _rows "ASan|${ENABLE_ASAN}|ENABLE_ASAN")
    list(APPEND _rows "UBSan|${ENABLE_UBSAN}|ENABLE_UBSAN")
    list(APPEND _rows "TSan|${ENABLE_TSAN}|ENABLE_TSAN")
    list(APPEND _rows "clang-tidy|${ENABLE_CLANG_TIDY}|ENABLE_CLANG_TIDY")
    list(APPEND _rows "cppcheck|${ENABLE_CPPCHECK}|ENABLE_CPPCHECK")
    list(APPEND _rows "Coverage|${ENABLE_COVERAGE}|ENABLE_COVERAGE")
    # Performance section
    list(APPEND _rows "---|---|---")
    list(APPEND _rows "LTO|${ENABLE_LTO}|ENABLE_LTO")

    if(PGO_MODE AND NOT PGO_MODE STREQUAL "")
        list(APPEND _rows "PGO|${PGO_MODE}|PGO_MODE")
    else()
        list(APPEND _rows "PGO|OFF|PGO_MODE")
    endif()

    # Compiler cache: read the launcher set by BuildCache.cmake
    if(CMAKE_CXX_COMPILER_LAUNCHER)
        get_filename_component(_cache_name "${CMAKE_CXX_COMPILER_LAUNCHER}" NAME)
        list(APPEND _rows "Build cache|${_cache_name}|ENABLE_CCACHE")
    else()
        list(APPEND _rows "Build cache|OFF|ENABLE_CCACHE")
    endif()

    list(APPEND _rows "---|---|---")
    list(APPEND _rows "Qt|${ENABLE_QT}|ENABLE_QT")
    list(APPEND _rows "Boost|${ENABLE_BOOST}|ENABLE_BOOST")
    list(APPEND _rows "Docs|${ENABLE_DOCS}|ENABLE_DOCS")

    # Compute column widths
    set(_w1 8)
    set(_w2 5)
    foreach(_r IN LISTS _rows)
        string(REPLACE "|" ";" _parts "${_r}")
        list(GET _parts 0 _l)
        list(GET _parts 1 _v)
        string(LENGTH "${_l}" _ll)
        string(LENGTH "${_v}" _vl)
        if(_ll GREATER _w1)
            set(_w1 ${_ll})
        endif()
        if(_vl GREATER _w2)
            set(_w2 ${_vl})
        endif()
    endforeach()

    math(EXPR _total "${_w1} + ${_w2} + 35")
    string(REPEAT "-" ${_total} _line)
    message(STATUS "")
    message(STATUS "┌${_line}┐")
    message(STATUS "│  Build Configuration Summary")
    message(STATUS "├${_line}┤")

    foreach(_r IN LISTS _rows)
        string(REPLACE "|" ";" _parts "${_r}")
        list(GET _parts 0 _l)
        list(GET _parts 1 _v)
        list(GET _parts 2 _n)

        if(_l STREQUAL "---")
            message(STATUS "├${_line}┤")
            continue()
        endif()

        string(LENGTH "${_l}" _ll)
        string(LENGTH "${_v}" _vl)
        math(EXPR _lpad "${_w1} - ${_ll}")
        math(EXPR _vpad "${_w2} - ${_vl}")
        string(REPEAT " " ${_lpad} _ls)
        string(REPEAT " " ${_vpad} _vs)

        if(_n AND NOT _n STREQUAL "")
            message(STATUS "│  ${_l}${_ls}  ${_v}${_vs}  (-D${_n})")
        else()
            message(STATUS "│  ${_l}${_ls}  ${_v}")
        endif()
    endforeach()

    message(STATUS "└${_line}┘")
    message(STATUS "")

    # ── Write FeatureFlags.h directly ──────────────────────────────────────────
    # Note: file(CONFIGURE) processes @VAR@ substitutions but NOT CMake variables
    # directly in CONTENT. We build the full string first, then write it.
    set(_header
"// FeatureFlags.h — AUTO-GENERATED by cmake/FeatureFlags.cmake
// DO NOT EDIT — regenerated on every CMake configure run.
// Source of truth: PROJECT_ALL_OPTIONS in cmake/ProjectConfigs.cmake
#pragma once

${_defines}
// ── Runtime inspection ─────────────────────────────────────────────────────
#include <string_view>
#include <array>

namespace project_features {

struct Feature {
    std::string_view name;
    bool             enabled;
};

inline constexpr std::array features = {
${_array_entries}};

} // namespace project_features
")

    file(WRITE "${GENERATED_DIR}/FeatureFlags.h" "${_header}")

    set(FEATURE_FLAGS_INCLUDE_DIR "${GENERATED_DIR}" PARENT_SCOPE)
    message(STATUS "FeatureFlags.h generated → ${GENERATED_DIR}/FeatureFlags.h")
endfunction()


# Attach FeatureFlags.h include path to a target.
function(target_add_feature_flags target)
    target_include_directories(${target} PUBLIC
        $<BUILD_INTERFACE:${CMAKE_BINARY_DIR}/generated/project>
        $<INSTALL_INTERFACE:include>
    )
endfunction()
"""
