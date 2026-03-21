# cmake/FeatureFlags.cmake
# Generates include/FeatureFlags.h — a project-wide header that exposes
# every CMake build option as a C++ preprocessor macro.
#
# Call once from root CMakeLists.txt (after ProjectConfigs):
#   include(FeatureFlags)
#   generate_feature_flags()
#
# Then make it available to a target:
#   target_include_directories(<target> PUBLIC
#       $<BUILD_INTERFACE:${CMAKE_BINARY_DIR}/generated/project>)

function(generate_feature_flags)
    set(GENERATED_DIR "${CMAKE_BINARY_DIR}/generated/project")
    file(MAKE_DIRECTORY "${GENERATED_DIR}")

    # Map CMake booleans → variables the .h.in template reads
    if(BUILD_SHARED_LIBS)
        set(PROJECT_SHARED_LIBS 1)
        set(PROJECT_FEATURE_LIBRARY_TYPE "Shared")
    else()
        set(PROJECT_SHARED_LIBS 0)
        set(PROJECT_FEATURE_LIBRARY_TYPE "Static")
    endif()

    # Each option maps to FEATURE_<NAME> (1 or 0)
    foreach(_opt
        UNIT_TESTS GTEST CATCH2 BOOST_TEST
        ASAN UBSAN TSAN
        CLANG_TIDY CPPCHECK COVERAGE
        QT QML BOOST DOCS
    )
        if(ENABLE_${_opt})
            set(FEATURE_${_opt} 1)
        else()
            set(FEATURE_${_opt} 0)
        endif()
    endforeach()

    # QTest follows Qt
    if(ENABLE_QT)
        set(FEATURE_QTEST 1)
    else()
        set(FEATURE_QTEST 0)
    endif()

    configure_file(
        "${CMAKE_CURRENT_FUNCTION_LIST_DIR}/FeatureFlags.h.in"
        "${GENERATED_DIR}/FeatureFlags.h"
    )

    # Export the include path as a global variable so root CMakeLists.txt
    # can forward it to all targets via an INTERFACE library.
    set(FEATURE_FLAGS_INCLUDE_DIR "${GENERATED_DIR}" PARENT_SCOPE)

    message(STATUS "FeatureFlags generated → ${GENERATED_DIR}/FeatureFlags.h")

    # ── Build configuration summary table ────────────────────────────────────
    # Collect column data
    set(_rows)
    macro(_row _label _val _note)
        list(APPEND _rows "${_label}|${_val}|${_note}")
    endmacro()

    if(BUILD_SHARED_LIBS)
        set(_link_type "Shared")
    else()
        set(_link_type "Static")
    endif()

    set(_btype "${CMAKE_BUILD_TYPE}")
    if(NOT _btype)
        set(_btype "(multi-config)")
    endif()

    set(_cxx "C++${CMAKE_CXX_STANDARD}")

    _row("Project"          "${PROJECT_NAME} v${PROJECT_VERSION}"  "")
    _row("CMake"            "${CMAKE_VERSION}"                      "min 3.25")
    _row("Build type"       "${_btype}"                             "")
    _row("Libraries"        "${_link_type}"                         "BUILD_SHARED_LIBS")
    _row("C++ standard"     "${_cxx}"                               "CMAKE_CXX_STANDARD")
    _row("Compiler"         "${CMAKE_CXX_COMPILER_ID} ${CMAKE_CXX_COMPILER_VERSION}" "")
    _row("---"              "---"                                   "---")
    _row("Unit tests"       "${ENABLE_UNIT_TESTS}"                  "ENABLE_UNIT_TESTS")
    if(ENABLE_UNIT_TESTS)
        if(ENABLE_GTEST)
            _row("Test framework"  "GoogleTest"                     "ENABLE_GTEST")
        elseif(ENABLE_CATCH2)
            _row("Test framework"  "Catch2"                         "ENABLE_CATCH2")
        elseif(ENABLE_BOOST_TEST)
            _row("Test framework"  "Boost.Test"                     "ENABLE_BOOST_TEST")
        elseif(ENABLE_QT)
            _row("Test framework"  "QTest"                          "ENABLE_QT")
        else()
            _row("Test framework"  "(none)"                         "")
        endif()
    endif()
    _row("---"              "---"                                   "---")
    _row("ASan"             "${ENABLE_ASAN}"                        "ENABLE_ASAN")
    _row("UBSan"            "${ENABLE_UBSAN}"                       "ENABLE_UBSAN")
    _row("TSan"             "${ENABLE_TSAN}"                        "ENABLE_TSAN")
    _row("clang-tidy"       "${ENABLE_CLANG_TIDY}"                  "ENABLE_CLANG_TIDY")
    _row("cppcheck"         "${ENABLE_CPPCHECK}"                    "ENABLE_CPPCHECK")
    _row("Coverage"         "${ENABLE_COVERAGE}"                    "ENABLE_COVERAGE")
    _row("---"              "---"                                   "---")
    _row("Qt"               "${ENABLE_QT}"                          "ENABLE_QT")
    _row("Boost"            "${ENABLE_BOOST}"                       "ENABLE_BOOST")
    _row("Docs"             "${ENABLE_DOCS}"                        "ENABLE_DOCS")

    # Compute column widths
    set(_w1 8)   # label min
    set(_w2 5)   # value min
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

    # Print table
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

        # Pad label and value
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
endfunction()


# Helper: attach FeatureFlags.h to an existing target
function(target_add_feature_flags target)
    target_include_directories(${target} PUBLIC
        $<BUILD_INTERFACE:${CMAKE_BINARY_DIR}/generated/project>
        $<INSTALL_INTERFACE:include>
    )
endfunction()
