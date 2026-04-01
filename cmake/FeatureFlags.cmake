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
    set(_defines "// BUILD_SHARED_LIBS\n#define PROJECT_SHARED_LIBS ${_shared}\n#define PROJECT_LIBRARY_TYPE \"${_lib_type}\"\n\n")

    foreach(_opt IN LISTS PROJECT_ALL_OPTIONS)
        if(ENABLE_${_opt})
            set(_val 1)
        else()
            set(_val 0)
        endif()
        string(APPEND _defines "// ENABLE_${_opt}\n#define FEATURE_${_opt} ${_val}\n")
    endforeach()

    if(ENABLE_QT)
        string(APPEND _defines "// ENABLE_QT → QTest\n#define FEATURE_QTEST 1\n")
    else()
        string(APPEND _defines "// ENABLE_QT → QTest\n#define FEATURE_QTEST 0\n")
    endif()

    # ── Build features[] entries ───────────────────────────────────────────────
    set(_array_entries "    Feature{\"shared_libs\", bool(PROJECT_SHARED_LIBS)},\n")
    foreach(_opt IN LISTS PROJECT_ALL_OPTIONS)
        string(TOLOWER "${_opt}" _opt_lower)
        string(APPEND _array_entries "    Feature{\"${_opt_lower}\", bool(FEATURE_${_opt})},\n")
    endforeach()
    string(APPEND _array_entries "    Feature{\"qtest\", bool(FEATURE_QTEST)},\n")

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
