# cmake/IWYU.cmake
#
# Include-What-You-Use (IWYU) integration.
#
# Usage:
#   include(IWYU)
#   enable_iwyu(<target> [REQUIRED] [EXTRA_OPTS ...])
#
# Options:
#   REQUIRED  — Fail the configure step if iwyu is not found (default: WARNING only).
#   EXTRA_OPTS — Additional iwyu flags, e.g. "--no_fwd_decls".
#
# Global option:
#   -DENABLE_IWYU=ON  applies enable_iwyu() to every target that includes this module.
#
# Per-target disable override:
#   set_target_properties(<target> PROPERTIES CXX_INCLUDE_WHAT_YOU_USE "")
#
# Notes:
#   - IWYU runs as a compiler launcher alongside the normal build.
#   - Output is captured by CMake and printed per-TU.
#   - Works best with Clang-based IWYU builds; GCC-built IWYU has limitations.

find_program(IWYU_EXECUTABLE
    NAMES include-what-you-use iwyu
    DOC   "Path to the include-what-you-use binary")

if(IWYU_EXECUTABLE)
    message(STATUS "[IWYU] Found: ${IWYU_EXECUTABLE}")
else()
    message(STATUS "[IWYU] include-what-you-use not found — enable_iwyu() will be a no-op")
endif()

function(enable_iwyu target)
    cmake_parse_arguments(_iwyu "REQUIRED" "" "EXTRA_OPTS" ${ARGN})

    if(NOT IWYU_EXECUTABLE)
        if(_iwyu_REQUIRED)
            message(FATAL_ERROR "[IWYU] include-what-you-use is required but was not found")
        else()
            message(WARNING "[IWYU] enable_iwyu(${target}): iwyu not found, skipping")
            return()
        endif()
    endif()

    set(_iwyu_cmd "${IWYU_EXECUTABLE}")
    # Standard useful opts: mapping files + pragma-once support
    list(APPEND _iwyu_cmd
        "-Xiwyu" "--mapping_file=${CMAKE_SOURCE_DIR}/cmake/iwyu_mappings.imp"
        "-Xiwyu" "--cxx17ns"
        "-Xiwyu" "--quoted_includes_first"
    )

    # Append any caller-provided extra opts (each opt wrapped in -Xiwyu)
    foreach(_opt IN LISTS _iwyu_EXTRA_OPTS)
        list(APPEND _iwyu_cmd "-Xiwyu" "${_opt}")
    endforeach()

    set_target_properties("${target}" PROPERTIES
        CXX_INCLUDE_WHAT_YOU_USE "${_iwyu_cmd}")

    message(STATUS "[IWYU] Enabled for target: ${target}")
endfunction()

# Auto-apply when ENABLE_IWYU is set globally (set via -DENABLE_IWYU=ON or tool.toml).
# Individual targets can opt out via: set_target_properties(... CXX_INCLUDE_WHAT_YOU_USE "")
option(ENABLE_IWYU "Run include-what-you-use on all targets" OFF)
